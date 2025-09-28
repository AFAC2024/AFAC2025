import os
import re
import json
import logging
import argparse
from typing import Dict, List, Optional
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from rule_extractor import RuleExtractorTool
from rule_definition_finder import RuleDefinitionFinderTool

log_file_path = './relevance_marker_agent.log' 
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if logger.hasHandlers():
    logger.handlers.clear()

file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logging.info(f"日志系统初始化完成，日志将输出到控制台和文件: {log_file_path}")

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE")

llm = ChatOpenAI(
    temperature=1.0, 
    model_name="qwen2.5-72b-instruct",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_API_BASE"),
    extra_body={"enable_thinking": False}
)

prompt_template = """
你是一个严谨、专注的保险文档相关性分析专家。
你的唯一任务是：判断给定的【文档内容】是否与【核心校验规则】的【详细释义】相关。

---
【上下文信息】
- **待校验规则ID**: {rule_id}
- **核心校验规则**: {rule_text}

---
【核心任务】

请仔细阅读以下【规则详细释义】，并判断【文档内容】中是否包含与释义中 对规则的"核心定义" 以及 规则相关的 "关键内容" 。并且注意 "注意事项"（若有）中与其他规则的关键区分点，专注于判断当前规则，不要与其他规则混淆。

1.  **规则详细释义 (来自知识库)**:
{rule_detailed_definition}

2.  **文档内容**:
{document_content}

---
【任务指令与输出格式】

1.  **分析**: 在你的思考过程中，对比【文档内容】和【规则详细释义】。
    - 如果【文档内容】中明确提及、讨论或暗示了【规则详细释义】中的核心概念，则它们是相关的。
    - 如果【文档内容】完全是无关话题（例如，规则是关于“等待期”，但文档内容是关于“如何缴费”），则它们不相关。

2.  **决策**: 根据你的分析，做出最终判断。

3.  **输出**: **严格按照**下面的JSON格式输出你的判断结果，不要添加任何额外的解释或文字。
```json
{{
  "rule_id": "{rule_id}",
  "is_related": <true_or_false>
}}
```
- 将 `<true_or_false>` 替换为 `true` (如果相关) 或 `false` (如果不相关)。

现在，请开始分析并生成JSON输出。
"""

prompt = PromptTemplate.from_template(prompt_template)
chain = prompt | llm | StrOutputParser()


def clean_llm_json_output(llm_output: str) -> str:
    """从LLM返回的文本中，精准提取出被```json ... ```包裹的JSON字符串。"""
    match = re.search(r"```json\s*(\{.*?\})\s*```", llm_output, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        stripped_output = llm_output.strip()
        if stripped_output.startswith('{') and stripped_output.endswith('}'):
            return stripped_output
    logging.warning("在LLM输出中未找到有效的JSON块。")
    return ""


# --- 4. 核心处理函数 ---
def run_relevance_marking(
    batch_file_path: str,
    rules_file_path: str,
    rule_extractor: RuleExtractorTool,
    definition_finder: RuleDefinitionFinderTool
) -> Optional[List[Dict]]:
    """
    处理单个batch文件，返回其与所有相关规则的相关性判断列表。
    """
    logging.info(f"开始为文件进行相关性标记: {batch_file_path}")
    try:
        # 步骤 1: 获取文档内容、类型和相关规则
        tool_input_json = json.dumps({
            "batch_file_path": batch_file_path,
            "rules_file_path": rules_file_path
        })
        context_data_str = rule_extractor._run(tool_input_json)
        context_data = json.loads(context_data_str)

        document_content = context_data.get("document_content")
        material_type_code = context_data.get("material_type_code", "UNKNOWN")
        all_matching_rules = context_data.get("all_matching_rules", [])

        if not document_content or not all_matching_rules:
            logging.warning(f"内容或规则为空，跳过文件: {batch_file_path}")
            return None

        all_marks = []
        logging.info(f"发现 {len(all_matching_rules)} 条匹配规则，开始逐一判断相关性...")

        for i, rule_analysis in enumerate(all_matching_rules):
            rule_id = rule_analysis.get('rule_id', '未知ID')
            rule_core_concept = rule_analysis.get('rule', '未知规则内容')
            
            logging.info(f"--- (规则 {i+1}/{len(all_matching_rules)}) 判断 Rule ID: {rule_id} ---")

            # 步骤 2: 获取规则详细释义
            tool_input_json_2 = json.dumps({"core_concept": rule_core_concept})
            detailed_definition = definition_finder._run(tool_input_json_2)

            # 步骤 3: 调用LLM进行相关性判断
            logging.info(f"为规则 '{rule_core_concept}' 调用LLM进行相关性判断...")
            llm_output_str = chain.invoke({
                "document_content": document_content,
                "rule_id": rule_id,
                "rule_text": rule_core_concept,
                "rule_detailed_definition": detailed_definition
            })

            # 步骤 4: 解析LLM输出的标记
            mark_json_str = clean_llm_json_output(llm_output_str)
            if not mark_json_str:
                logging.error(f"LLM为规则 {rule_id} 返回了空响应，跳过此规则。文件: {batch_file_path}")
                continue

            mark_data = json.loads(mark_json_str)

            # 步骤 5: 构建包含所有信息的标记对象，无论true还是false
            final_mark = {
                "rule_id": mark_data.get("rule_id"),
                "material_type_code": material_type_code,
                "is_related": mark_data.get("is_related", False),
                "source_file": batch_file_path
            }
            all_marks.append(final_mark)
            logging.info(f"判断完成: Rule ID {rule_id}, 相关性: {final_mark['is_related']}")

        logging.info(f"文件标记完成: {batch_file_path}, 共生成 {len(all_marks)} 条判断记录。")
        return all_marks

    except Exception as e:
        logging.error(f"处理文件 {batch_file_path} 时发生严重错误: {e}", exc_info=True)
        return None


def find_target_files(root_dir: str) -> List[str]:
    """
    扫描指定目录（可以是根目录或单个material文件夹），递归查找所有 'batch_*.md' 文件。
    """
    target_files = []
    logging.info(f"开始在目录 {root_dir} 中扫描 batch_*.md 文件...")
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".md") and filename.startswith("batch_"):
                full_path = os.path.join(dirpath, filename)
                target_files.append(full_path)
    logging.info(f"扫描完成，在 {root_dir} 中共找到 {len(target_files)} 个目标文件。")
    return sorted(target_files)

def find_material_dirs(root_dir: str) -> List[str]:
    """
    扫描根目录，查找所有符合 'm_*' 模式的文件夹。
    """
    material_dirs = []
    logging.info(f"开始在根目录 {root_dir} 中扫描 'm_*' 文件夹...")
    if not os.path.isdir(root_dir):
        logging.error(f"提供的输入目录不存在或不是一个目录: {root_dir}")
        return []
        
    for item in os.listdir(root_dir):
        path = os.path.join(root_dir, item)
        if os.path.isdir(path) and item.startswith("m_"):
            material_dirs.append(path)
    logging.info(f"扫描完成，共找到 {len(material_dirs)} 个 'm_*' 文件夹。")
    return sorted(material_dirs)


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_data_dir = os.path.join(current_dir, "测试 B 集", "chunck_data")
    default_rules_path = os.path.join(current_dir, "测试 B 集", "data.jsonl")
    default_definition_path = os.path.join(current_dir, "rule.md")

    parser = argparse.ArgumentParser(description="文档与规则相关性标记代理")
    parser.add_argument("--input_dir", type=str, default=input_data_dir, help="包含 m_* 文件夹的根目录")
    parser.add_argument("--batch_file", type=str, help="（可选）单个批处理文件的路径，用于单文件调试")
    parser.add_argument("--rules_file", type=str, default=default_rules_path, help="规则文件的路径")
    parser.add_argument("--definition_file", type=str, default=default_definition_path, help="规则详细释义文件的路径")
    args = parser.parse_args()

    try:
        rule_extractor = RuleExtractorTool()
        definition_finder = RuleDefinitionFinderTool(knowledge_base_path=args.definition_file)
    except Exception as e:
        logging.error(f"初始化工具时失败: {e}", exc_info=True)
        exit(1)


    if args.batch_file:
        logging.info(f"--- 开始单文件处理模式: {args.batch_file} ---")
        marks_list = run_relevance_marking(
            batch_file_path=args.batch_file,
            rules_file_path=args.rules_file,
            rule_extractor=rule_extractor,
            definition_finder=definition_finder,
        )
        if marks_list:
            print(json.dumps(marks_list, indent=2, ensure_ascii=False))
        logging.info("--- 单文件处理完成 ---")
    else:
        logging.info("--- 开始批量处理模式 ---")
        material_dirs = find_material_dirs(args.input_dir)
        
        if not material_dirs:
            logging.warning(f"在目录 {args.input_dir} 未找到任何 'm_*' 文件夹。")
        else:
            total_materials = len(material_dirs)
            total_records_all = 0
            
            # 1. 外层循环遍历每个 material 文件夹
            for i, material_dir in enumerate(material_dirs):
                material_id = os.path.basename(material_dir)
                logging.info(f"--- 开始处理 Material 文件夹 ({i+1}/{total_materials}): {material_id} ---")

                # 2. 在当前 material 文件夹内查找所有 batch 文件
                batch_files_in_dir = find_target_files(material_dir)
                if not batch_files_in_dir:
                    logging.warning(f"在 {material_id} 中未找到任何 batch 文件，跳过。")
                    continue

                # 3. 为当前 material 文件夹创建一个临时的结果列表
                current_material_results = []
                
                # 4. 内层循环处理该文件夹下的所有 batch 文件
                for file_path in batch_files_in_dir:
                    logging.info(f"--- 正在处理文件: {os.path.basename(file_path)} ---")
                    marks_list = run_relevance_marking(
                        batch_file_path=file_path,
                        rules_file_path=args.rules_file,
                        rule_extractor=rule_extractor,
                        definition_finder=definition_finder,
                    )
                    if marks_list:
                        current_material_results.extend(marks_list)

                # 5. 当前文件夹所有文件处理完毕后，立即写入结果
                if current_material_results:
                    output_file_path = os.path.join(material_dir, "relevance_marks.json")
                    try:
                        with open(output_file_path, 'w', encoding='utf-8') as f:
                            json.dump(current_material_results, f, indent=2, ensure_ascii=False)
                        logging.info(f"成功为 '{material_id}' 写入 {len(current_material_results)} 条记录到 -> {output_file_path}")
                        total_records_all += len(current_material_results)
                    except Exception as e:
                        logging.error(f"为 '{material_id}' 写入文件时失败: {e}")
                else:
                    logging.info(f"文件夹 '{material_id}' 未生成任何有效标记，不创建文件。")

                logging.info(f"--- 完成处理 Material 文件夹: {material_id} ---")

            logging.info("--- 批量处理全部完成 ---")
            logging.info(f"总共处理了 {total_materials} 个 material 文件夹。")
            logging.info(f"总共生成了 {total_records_all} 条相关性判断记录。")