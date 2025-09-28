import os
import re
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Union
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from rule_extractor import RuleExtractorTool
from rule_definition_finder import RuleDefinitionFinderTool
from text_slicer_tool import TextSlicerTool
from dotenv import load_dotenv

log_file_path = './feature_extract_agent_log.log' 

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
你是一个严谨的保险文档规则校验专家。
你的任务是：深入理解【核心校验概念】和它的【详细释义】，然后在【文档内容】中精准地识别所有相关的具体信息的位置，生成切片指令。

---
【上下文信息】

- **当前文档的素材类型**: {material_type_name}
- **待校验规则ID**: {rule_id}

---
【核心任务】

根据下面的【核心校验概念】及其【详细释义】，在【文档内容】中提取证据。

1.  **核心校验概念**: {rule_text}

2.  **规则详细释义 (来自知识库)**:
{rule_detailed_definition}

3.  **文档内容**:
{document_content}

---
【任务指令与输出格式】

**第一步：定位证据**
在【文档内容】中，寻找与【规则详细释义】中描述的"关键提取内容"完全匹配的具体信息。

**第二步：生成切片指令**
为每个找到的证据生成精确的位置信息，包括关键词和行号范围。

**【极端重要的规则】**
1.  **精确引用原则**: `start_keyword` 和 `end_keyword` **必须是【文档内容】中原封不动的、一字不差的文本片段**。
    - **严禁**自行编造、总结、修改或缩写任何文字。
    - 如果在【文档内容】中找到的`start_keyword`的最后一个字符是换行符`\n`且`start_keyword`不能组成一个完整语义,一定要保证`end_keyword`存在且不为空并且在`start_keyword`之后，使得`start_keyword` 和 `end_keyword` 范围内的【文档内容】可以组成一句或多句完整的自然语言。
2.  **关键词选择原则**:
    - `start_keyword` 建议范围10-15个字符，以确保在文档中的唯一性，从而精确定位。
    - `end_keyword` 建议范围8-15个字符，用于界定范围，由于其代表一段自然语言的结尾，可以是一句话的最后8到16个字符。
3.  **单行原则**: `start_keyword` 和 `end_keyword` **必须来自【文档内容】中的某一个单行**。换行符号为`\n`，严禁将多行的文本合并成一个关键词。
4.  **顺序原则**: 生成的切片指令的`start_keyword`必须按照在【文档内容】中出现的先后顺序排列，即`start_keyword`按行号从小到大排序后再输出。

**[示例 1]**
【文档内容】:"在保险期间内，若被保险人在本合同等待期后，首次罹患并在保险公司认可\n的医院由专科医生确诊为本合同约定的乳腺癌，保险公司按保险单上载明的\n女性疾病保险金额给付乳腺癌保险金，本合同效力终止。\n"
`start_keyword`:"在保险期间内，若被保险人在本合同等待期后，首次罹患并在保险公司认可\n"
`end_keyword`:"女性疾病保险金额给付乳腺癌保险金，本合同效力终止。\n"


**严格按照以下JSON格式输出**：

```json
{{
  "rule_validation": {{
    "rule_id": "{rule_id}",
    "rule_text": "{rule_text}",
    "is_related": true
  }},
  "slice_instructions": [
    {{
      "location": {{
        "start_keyword": "产品的具体关键词",
        "end_keyword": "结束的关键词（可选）",
      }}
    }}
  ]
}}
```

现在，请开始分析并生成JSON输出。
"""

prompt = PromptTemplate.from_template(prompt_template)
chain = prompt | llm | StrOutputParser()

# --- 3. 辅助函数 ---
MATERIAL_TYPE_MAP = {
    "CLAUSE": "条款", "INSURE_NOTICE": "投保须知", "HEALTH_INFORM": "健康告知",
    "HEAD_IMG": "头图", "INTRODUCE_IMG": "图文说明", "H5": "H5资料",
    "INSURANCE_POLICY": "电子保单", "PRODUCT_MANUAL": "产品说明书",
    "ADDITIONAL_AGREEMENT": "特别约定", "LIABILITY_EXCLUSION": "免责说明"
}

def parse_file_info(file_path: str) -> Dict[str, str]:
    """极简版本，只负责从路径中解析 material_id，主要用于日志记录。"""
    abs_path = os.path.abspath(file_path)
    material_id_match = re.search(r'/(m_\d+[a-z]?)/', abs_path)
    return {
        "material_id": material_id_match.group(1) if material_id_match else "未知"
    }

def clean_llm_json_output(llm_output: str) -> str:
    """
    从LLM返回的、可能包含聊天内容的文本中，精准提取出被```json ... ```包裹的JSON字符串。
    """
    match = re.search(r"```json\s*(\{.*?\})\s*```", llm_output, re.DOTALL)
    
    if match:
        # 如果找到匹配项，返回捕获组1的内容（也就是花括号内的所有内容）
        return match.group(1).strip()
    else:
        # 作为备用方案，如果模型有时不带```json标记，只返回裸的JSON
        # 我们就尝试直接清理并返回
        stripped_output = llm_output.strip()
        if stripped_output.startswith('{') and stripped_output.endswith('}'):
            return stripped_output
            
    logging.warning("在LLM输出中未找到有效的JSON块。")
    return ""

def run_feature_extraction(
    batch_file_path: str,
    rules_file_path: str,
    rule_extractor: RuleExtractorTool,
    definition_finder: RuleDefinitionFinderTool,
    slicer_tool: TextSlicerTool
) -> Optional[List[Dict]]: # 返回值现在是一个字典列表或None
    logging.info(f"开始处理文件: {batch_file_path}")
    try:
        # 步骤 1: 调用工具获取文档内容和所有相关规则
        tool_input_json = json.dumps({
            "batch_file_path": batch_file_path,
            "rules_file_path": rules_file_path
        })
        context_data_str = rule_extractor._run(tool_input_json)
        context_data = json.loads(context_data_str)

        # 步骤 2: 解包信息
        document_content = context_data.get("document_content")
        material_type_code = context_data.get("material_type_code", "未知")
        material_type_name = context_data.get("material_type_name", "未知")
        # 获取规则列表，而不是单个规则分析
        all_matching_rules = context_data.get("all_matching_rules", [])

        if not document_content:
            logging.warning(f"文件内容为空，跳过处理: {batch_file_path}")
            return None

        if not all_matching_rules:
            file_info = parse_file_info(batch_file_path)
            logging.warning(f"未找到与 material_id '{file_info['material_id']}' 匹配的规则，跳过处理。")
            return None

        final_results_list = [] # 用于存储此文件所有规则的处理结果
        
        logging.info(f"发现 {len(all_matching_rules)} 条相关规则，开始逐一处理...")

        for i, rule_analysis in enumerate(all_matching_rules):
            rule_id = rule_analysis.get('rule_id', '未知ID')
            rule_core_concept = rule_analysis.get('rule', '未知规则内容')
            
            logging.info(f"--- (规则 {i+1}/{len(all_matching_rules)}) 开始处理 Rule ID: {rule_id} ---")

            # 步骤 3: 获取规则详细释义
            tool_input_json_2 = json.dumps({"core_concept": rule_core_concept})
            detailed_definition = definition_finder._run(tool_input_json_2)

            # 步骤 4: 调用LLM进行分析
            logging.info(f"将文档内容及核心校验概念 '{rule_core_concept}' (来自规则ID: {rule_id}) 喂给LLM进行分析...")
            llm_output_str = chain.invoke({
                "document_content": document_content,
                "material_type_name": material_type_name,
                "rule_id": rule_id,
                "rule_text": rule_core_concept,
                "rule_detailed_definition": detailed_definition
            })

            # 步骤 5: 解析LLM输出
            slice_instructions_json = clean_llm_json_output(llm_output_str)
            if not slice_instructions_json:
                logging.error(f"LLM为规则 {rule_id} 返回了空响应，跳过此规则。文件: {batch_file_path}")
                continue # 跳过当前循环，处理下一条规则

            slice_instructions_data = json.loads(slice_instructions_json)

            # 步骤 6: 调用切片工具
            logging.info(f"为规则 {rule_id} 调用切片工具进行特征提取...")
            tool_input = json.dumps({
                "document_content": document_content,
                "rule_validation": slice_instructions_data.get("rule_validation", {}),
                "slice_instructions": slice_instructions_data.get("slice_instructions", [])
            })
            final_result_str = slicer_tool._run(tool_input)

            if not final_result_str:
                logging.error(f"切片工具为规则 {rule_id} 返回空结果。文件: {batch_file_path}")
                continue # 跳过

            final_result = json.loads(final_result_str)

            # 步骤 7: 添加文件和类型信息到单个结果中
            final_result.update({
                "file_path": batch_file_path,
                "material_type_code": material_type_code
            })
            
            # 将处理好的单个结果添加到列表中
            final_results_list.append(final_result)
            logging.info(f"--- (规则 {i+1}/{len(all_matching_rules)}) 成功处理 Rule ID: {rule_id} ---")

        logging.info(f"文件处理完成: {batch_file_path}, 共生成 {len(final_results_list)} 条特征记录。")
        return final_results_list # 返回包含所有结果的列表

    except Exception as e:
        logging.error(f"处理文件 {batch_file_path} 时发生严重错误: {e}", exc_info=True)
        return None
    
def find_target_files(root_dir: str) -> List[str]:
    """
    扫描根目录，查找所有符合 'm_*/batch_*.md' 模式的文件。
    """
    target_files = []
    logging.info(f"开始在目录 {root_dir} 中扫描目标文件...")
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 筛选出当前目录下的 m_* 文件夹
        dirnames[:] = [d for d in dirnames if re.match(r'^m_.*', d)]
        
        # 筛选出当前目录下的 batch_*.md 文件
        for filename in filenames:
            if re.match(r'^batch_.*\.md$', filename):
                full_path = os.path.join(dirpath, filename)
                target_files.append(full_path)
                
    logging.info(f"扫描完成，共找到 {len(target_files)} 个目标文件。")
    return target_files

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_data_dir = os.path.join(current_dir, "samples", "chunck_data")
    output_dir = os.path.join(current_dir, "samples","feature")
    default_rules_path = os.path.join(current_dir, "samples", "data.jsonl")
    default_definition_path = os.path.join(current_dir, "rule.md")

    parser = argparse.ArgumentParser(description="特征提取代理")
    parser.add_argument("--batch_file", type=str, help="单个批处理文件的路径")
    parser.add_argument("--rules_file", type=str, default=default_rules_path, help="规则文件的路径")
    parser.add_argument("--definition_file", type=str, default=default_definition_path, help="规则详细释义文件的路径")
    args = parser.parse_args()

    os.makedirs(output_dir, exist_ok=True)

    rule_extractor = RuleExtractorTool()
    definition_finder = RuleDefinitionFinderTool(knowledge_base_path=args.definition_file)
    slicer_tool = TextSlicerTool()

    if args.batch_file:
        # 单文件处理模式
        logging.info(f"--- 开始单文件处理模式: {args.batch_file} ---")
        results_list = run_feature_extraction(
            batch_file_path=args.batch_file,
            rules_file_path=args.rules_file,
            rule_extractor=rule_extractor,
            definition_finder=definition_finder,
            slicer_tool=slicer_tool
        )
        if results_list:
            # 打印所有结果
            print(json.dumps(results_list, indent=2, ensure_ascii=False))
        logging.info("--- 单文件处理完成 ---")
    else:
        # 批量处理模式
        logging.info("--- 开始批量处理模式 ---")
        target_files = find_target_files(input_data_dir)
        if not target_files:
            logging.info(f"在目录 {input_data_dir} 未找到任何 'batch_*.md' 文件。")
        else:
            total_files = len(target_files)
            total_success_records = 0 # 记录成功的记录总数，而不是文件数
            initialized_files = set()

            logging.info(f"发现 {total_files} 个文件，开始处理...")

            for i, file_path in enumerate(target_files):
                logging.info(f"--- 正在处理第 {i+1}/{total_files} 个文件: {file_path} ---")

                results_list = run_feature_extraction(
                    batch_file_path=file_path,
                    rules_file_path=args.rules_file,
                    rule_extractor=rule_extractor,
                    definition_finder=definition_finder,
                    slicer_tool=slicer_tool
                )

                # 如果返回了结果列表（即使为空也继续，由内部逻辑处理）
                if results_list:
                    # 遍历这个文件产生的所有结果
                    for result in results_list:
                        try:
                            m_dir_name = os.path.basename(os.path.dirname(file_path))
                            material_type_code = result.get("material_type_code", "UNKNOWN")
                            
                            material_output_dir = os.path.join(output_dir, "materials", m_dir_name)
                            os.makedirs(material_output_dir, exist_ok=True)
                            output_file_path = os.path.join(material_output_dir, f"{material_type_code}_feature.jsonl")

                            file_key = (m_dir_name, material_type_code)
                            if file_key not in initialized_files:
                                logging.info(f"首次处理 '{m_dir_name}/{material_type_code}', 初始化输出文件: {output_file_path}")
                                with open(output_file_path, 'w', encoding='utf-8') as f:
                                    pass # 创建或清空文件
                                initialized_files.add(file_key)

                            with open(output_file_path, 'a', encoding='utf-8') as f:
                                json.dump(result, f, ensure_ascii=False)
                                f.write('\n')
                            
                            total_success_records += 1
                            logging.info(f"成功提取一条特征记录并追加到 -> {output_file_path}")

                        except Exception as e:
                            logging.error(f"写入结果时发生错误: {e}", exc_info=True)
            
            logging.info("--- 批量处理完成 ---")
            logging.info(f"总共处理了 {total_files} 个文件，成功提取了 {total_success_records} 条特征记录。")
            logging.info(f"结果已按 'm_*' 目录分组写入到 '{output_dir}' 目录中。")