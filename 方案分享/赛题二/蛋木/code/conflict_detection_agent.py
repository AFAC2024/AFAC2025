import json
import os
import collections
import glob
import logging
import itertools
from typing import Dict, List, Any, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from rule_extractor import RuleExtractorTool, FewshotExtractorTool
from rule_definition_finder import RuleDefinitionFinderTool
from conflict_reviewer_agent import ConflictReviewerAgent
from relevance_checker_agent import RelevanceCheckerAgent
    
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

class FocusedConflictAnalysis(BaseModel):
    is_conflict: bool = Field(description="在严格遵守'审计范围'的前提下，两份文档是否存在事实性冲突？")
    reason: str = Field(description="用一句话总结你的判断。若存在冲突，一定要明确说明两份文档内容的差异点。例如：有冲突时: '存在冲突，因等待期天数不同。全文1等待期30天，而全文2等待期90天';无冲突时:'无冲突，因两者在等待期描述上完全一致。")


class ConflictDetectionAgent:
    SIMPLIFIED_FOCUSED_PROMPT = """你是一名高效、严谨的保险条款审计专家。

【审计范围】
你的唯一任务是判断两份文档是否在以下【特定规则及对应权威定义】上存在事实性冲突。不许擅自根据规则及其定义文字进行随意扩展联想。你检测的内容不能跳出【规则权威定义】。
- **规则核心概念**: "{rule_text}"
- **规则权威定义**: "{rule_definition}"

【判别参考示例】
以下是关于“{rule_text}”这个主题的一个判别示例，请参考其分析逻辑和判别标准，但不要被其结论影响你的独立判断。
---
{fewshot_example}
---

【待审计的完整文档】
- **全文1** (来自 `{file1_path}`):
---
{text1}
---

- **全文2** (来自 `{file2_path}`):
---
{text2}
---

【任务指令】
1.  在【审计范围】内，仔细阅读并比较【全文1】和【全文2】中与【特定主题】相关的内容。
2.  如果发现关于此主题的描述存在明确的、事实性的矛盾（例如，数值不同、条件相悖），则判定为`is_conflict: true`。
3.  如果描述一致、互为补充、或其中一份/两份文档未提及此主题，则判定为`is_conflict: false`。
4.  请以指定的JSON格式返回你的最终判断和理由。

{format_instructions}
"""


    def __init__(self, llm_instance: ChatOpenAI, rule_extractor: RuleExtractorTool, definition_finder: RuleDefinitionFinderTool, fewshot_extractor: FewshotExtractorTool):
        parser = JsonOutputParser(pydantic_object=FocusedConflictAnalysis)
        prompt = ChatPromptTemplate.from_template(
            template=self.SIMPLIFIED_FOCUSED_PROMPT,
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        self.detection_chain = prompt | llm_instance | parser
        self.rule_extractor = rule_extractor
        self.definition_finder = definition_finder
        self.fewshot_extractor = fewshot_extractor  
        logging.info("精简聚焦型冲突检测Agent初始化完成 (已集成Few-shot能力)。")

    def _read_file_content(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logging.error(f"文件未找到: {file_path}")
            return ""
        return ""

    def _load_and_group_marks(self, marks_file_path: str) -> Dict[str, List[Dict]]:
        if not os.path.exists(marks_file_path): return {}
        with open(marks_file_path, 'r', encoding='utf-8') as f:
            marks_data = json.load(f)
        grouped_by_rule = collections.defaultdict(list)
        for mark in marks_data:
            if mark.get("is_related"):
                grouped_by_rule[mark["rule_id"]].append(mark)
        return dict(grouped_by_rule)

    def _detect_conflict_between_documents(self, pair: Tuple[Dict, Dict], rule_text: str, rule_definition: str, fewshot_example: str) -> Dict:
        mark1, mark2 = pair
        file1_path, file2_path = mark1['source_file'], mark2['source_file']
        text1, text2 = self._read_file_content(file1_path), self._read_file_content(file2_path)

        if not text1 or not text2:
            return {"is_conflict": False, "reason": "文件内容为空或无法读取"}
        
        input_data = {
            "rule_text": rule_text, 
            "rule_definition": rule_definition,
            "fewshot_example": fewshot_example, 
            "file1_path": os.path.basename(file1_path), 
            "file2_path": os.path.basename(file2_path),
            "text1": text1, 
            "text2": text2,
        }
        try:
            analysis_result = self.detection_chain.invoke(input_data)
            if isinstance(analysis_result, BaseModel): analysis_result = analysis_result.dict()
            return analysis_result
        except Exception as e:
            logging.warning(f"LangChain链在处理规则 {mark1['rule_id']} 时出错: {e}。将默认无冲突。")
            return {"is_conflict": False, "reason": f"LLM调用失败: {e}"}

    def run(self, folder_path: str, rules_file_path: str, reviewer_agent: ConflictReviewerAgent) -> List[Dict]:
        material_id = os.path.basename(folder_path)
        logging.info(f"\n======== 开始处理文件夹: {material_id} ========")
        marks_file_path = os.path.join(folder_path, "relevance_marks.json")
        grouped_marks = self._load_and_group_marks(marks_file_path)

        if not grouped_marks:
            logging.warning(f"文件夹 {material_id} 中没有相关的规则标记。")
            return []
        
        final_results = []
        for rule_id, marks in grouped_marks.items():
            logging.info(f"====== 开始检测规则: {rule_id} ======")
            
            potential_conflict_pairs = [
                p for p in itertools.combinations(marks, 2) if p[0]['material_type_code'] != p[1]['material_type_code']
            ]
            
            if not potential_conflict_pairs:
                logging.info(f"规则 {rule_id}: 无需比对。")
                final_results.append({"material_id": material_id, "rule_id": rule_id, "result": True})
                continue

            rule_text = self.rule_extractor.get_rule_text_by_id(rule_id=rule_id, rules_file_path=rules_file_path)
            if not rule_text:
                logging.error(f"无法为 rule_id '{rule_id}' 获取规则文本。跳过。")
                final_results.append({"material_id": material_id, "rule_id": rule_id, "result": True})
                continue
            
            rule_definition = self.definition_finder._run(json.dumps({"core_concept": rule_text}))

            # 获取 Few-shot 示例
            logging.info(f"正在为核心概念 '{rule_text}' 查找 few-shot 示例...")
            fewshot_example = self.fewshot_extractor.run(core_concept=rule_text)

            if fewshot_example.startswith("错误:"):
                logging.warning(fewshot_example) 
                fewshot_example = "无此规则的可用参考示例。"
            else:
                logging.info("成功获取到 few-shot 示例。")


            is_rule_conflicting = False
            for pair in potential_conflict_pairs:
                mark1, mark2 = pair
                file1_path, file2_path = mark1['source_file'], mark2['source_file']
                logging.info(f"--- 正在比对文件对: {os.path.basename(file1_path)} vs {os.path.basename(file2_path)}")
                
                conflict_result = self._detect_conflict_between_documents(
                    pair, rule_text, rule_definition, fewshot_example
                )
                
                if conflict_result.get("is_conflict", False):
                    logging.warning(f"    -> Agent2 初步检测到潜在冲突。理由: {conflict_result.get('reason')}")
                    logging.info("    -> [启动 Agent3 审查流程]")

                    review_result = reviewer_agent.run(
                        reason=conflict_result.get('reason'),
                        rule_text=rule_text,
                        file1_path=file1_path,
                        file2_path=file2_path
                    )
                    
                    if review_result.get("is_true_conflict"):
                        logging.warning(f"    -> [Agent3 审查通过] 确认存在事实性矛盾。理由: {review_result.get('justification')}")
                        logging.warning(f"!!! [冲突确认] 规则 {rule_id} 发现冲突。将不再检查该规则下的其他文件对。")
                        is_rule_conflicting = True
                        # 当对一个规则不确定、需要让agent检查所有相关文件的时候，把break注释掉
                        break
                    else:
                        logging.info(f"    -> [Agent3 审查驳回] 判定为伪冲突。理由: {review_result.get('justification')}")
                        logging.info(f"    -> 继续检查下一文件对...")
                
            final_output_result = not is_rule_conflicting
            final_results.append({"material_id": material_id, "rule_id": rule_id, "result": final_output_result})
            
            status_text = '检测到冲突' if is_rule_conflicting else '未检测到冲突'
            logging.info(f"--> 规则 {rule_id} 审计完成: {status_text}。最终结果: {final_output_result}")

        logging.info(f"======== 文件夹处理完毕: {material_id} ========")
        return final_results

# --- 日志与执行入口 ---
def setup_logging(log_dir: str):
    log_filename = "conflict_detect_agent.log"
    log_filepath = os.path.join(log_dir, log_filename)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if logger.hasHandlers(): logger.handlers.clear()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler = logging.FileHandler(log_filepath, mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    INPUT_DIR = os.path.join(current_dir, "测试 B 集", "chunck_data")
    OUTPUT_DIR = os.path.join(current_dir, "测试 B 集", "results")
    RULES_FILE = os.path.join(current_dir, "测试 B 集", "data.jsonl")
    DEFINITION_FILE = os.path.join(current_dir, "rule.md")
    FEWSHOT_FILE = os.path.join(current_dir, "fewshot.md")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    setup_logging(log_dir=OUTPUT_DIR)

    folder_pattern = os.path.join(INPUT_DIR, "m_*")
    folder_list = [d for d in glob.glob(folder_pattern) if os.path.isdir(d)]
    
    rule_extractor = RuleExtractorTool()
    definition_finder = RuleDefinitionFinderTool(knowledge_base_path=DEFINITION_FILE)
    fewshot_extractor = FewshotExtractorTool(fewshot_file_path=FEWSHOT_FILE) 
    
    # 首先创建最底层的Agent4，它依赖LLM和definition_finder
    agent4 = RelevanceCheckerAgent(
        llm_instance=llm,
        definition_finder=definition_finder
    )

    # 然后创建Agent3，它依赖LLM和Agent4
    agent3 = ConflictReviewerAgent(
        llm_instance=llm,
        agent4=agent4
    )

    # 最后创建Agent2，它依赖其他工具
    agent2 = ConflictDetectionAgent(
        llm_instance=llm,
        rule_extractor=rule_extractor,
        definition_finder=definition_finder,
        fewshot_extractor=fewshot_extractor
    )

    all_results = []
    for folder_path in sorted(folder_list):
        results = agent2.run(
            folder_path=folder_path, 
            rules_file_path=RULES_FILE,
            reviewer_agent=agent3 
        )
        all_results.extend(results)
    
    if all_results:
        output_file_path = os.path.join(OUTPUT_DIR, "result.jsonl")
        with open(output_file_path, 'w', encoding='utf-8') as f:
            for line in all_results:
                f.write(json.dumps(line, ensure_ascii=False) + '\n')
        logging.info(f"最终报告已生成: {output_file_path}")