import logging
import os
from typing import Dict
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.language_models.chat_models import BaseChatModel
from relevance_checker_agent import RelevanceCheckerAgent


class ConflictReviewResult(BaseModel):
    """定义了审查结果的数据结构。"""
    is_true_conflict: bool = Field(
        description="在严格区分'事实性矛盾'和'信息完整度差异'后，该理由是否描述了一个真实、直接的事实性矛盾？"
    )
    justification: str = Field(
        description="用一句话解释你做出此判断的理由。例如：'确认冲突，因等待期天数描述矛盾。'或'驳回冲突，因理由仅描述了信息缺失，而非事实矛盾。'"
    )


class ConflictReviewerAgent:
    """
    Agent3: 冲突审查员。
    职责：审查Agent2的报告，判断是否为【事实性矛盾】。如果是，则调用Agent4进行相关性检查。
    """
    
    REVIEWER_PROMPT = """
你是一名极其严谨、经验丰富的合同审计主管。你的唯一任务是审查下级审计员提交的一份冲突报告，并做出最终裁决。

【背景信息】
- **当前审计的规则主题**: "{rule_text}"
- **正在比对的文件**: `{file1_path}` vs `{file2_path}`

【下级审计员的报告】
下级审计员声称在上述两个文件中发现了与规则主题相关的冲突，并给出了以下理由：
> **冲突理由**: "{reason}"

【你的审查标准】
你必须严格遵循以下标准，区分“事实性矛盾”和“信息完整度差异”：

1.  **事实性矛盾 (这是你需要确认的【真冲突】)**
    - **定义**: 理由表明两个文件对【同一具体事项】给出了**不一致**的描述。
    - **示例**:
        - 存在冲突，因等待期天数不同。 (天数不同 -> 真冲突)
        - 存在冲突，文件A说“仅赔付A、B两种疾病”，文件B说“赔付A、B、C三种疾病”。(范围不同 -> 真冲突)
        - 存在冲突，因全文1描述的是个人公共交通工具意外伤害保险，而全文2描述的是畅玩无忧境外旅行意外险，产品全称不同。(产品名称不同 -> 真冲突)

2.  **信息完整度差异 (这是你需要驳回的【伪冲突】)**
    - **定义**: 一个文件详细描述了某个主题，而另一个文件【未明确定义】。这不构成事实上的矛盾，只是详略有别。
    - **示例**:
        - 存在冲突，因对'本公司认可的医院'的定义不同。全文1未明确定义，全文2定义为二级或二级以上的公立医院。(“未明确定义”属于一方缺失 -> 伪冲突)
        - 存在冲突，因全文1中免赔额为0，而全文2中免赔额由投保人和保险人协商确定并在保险单中载明。(两篇文章没有同时指明“在保险单中载明”也属于一方缺失 -> 伪冲突)
        - 存在冲突，存在冲突，因搬家费用补偿的免赔率不同。全文1免赔额（率）由投保人与保险人协商确定，而全文2搬家费用补偿每次事故绝对免赔率50%。（“与保险人协商确定”属于【定义模糊】-> 伪冲突）


【你的裁决任务】
根据上述【审查标准】，对下级审计员报告的“冲突理由”进行裁决。判断该理由是否真正揭示了一个【事实性矛盾】。
以指定的JSON格式返回你的最终裁决和理由。

{format_instructions}
"""

    def __init__(self, llm_instance: BaseChatModel, agent4: RelevanceCheckerAgent):
        """
        初始化冲突审查Agent。
        Args:
            llm_instance (BaseChatModel): LLM实例。
            agent4 (RelevanceCheckerAgent): 用于进行相关性检查的Agent4实例。
        """
        parser = JsonOutputParser(pydantic_object=ConflictReviewResult)
        prompt = ChatPromptTemplate.from_template(
            template=self.REVIEWER_PROMPT,
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        self.review_chain = prompt | llm_instance | parser
        self.agent4 = agent4 
        logging.info("Agent3: ConflictReviewerAgent 初始化完成，已链接到Agent4。")

    def run(self, reason: str, rule_text: str, file1_path: str, file2_path: str) -> Dict:
        """
        执行两阶段审查任务。
        """
        logging.info(f"    [Agent3] 阶段1: 审查理由 '{reason}' 是否为事实性矛盾。")
        
        input_data = {
            "reason": reason,
            "rule_text": rule_text,
            "file1_path": os.path.basename(file1_path),
            "file2_path": os.path.basename(file2_path),
        }

        try:
            # 阶段1: 判断是否为事实性矛盾
            review_result = self.review_chain.invoke(input_data)
            review_result = review_result.dict() if isinstance(review_result, BaseModel) else review_result

            # 如果不是事实性矛盾，直接返回结果，流程结束
            if not review_result.get("is_true_conflict"):
                logging.info(f"    [Agent3] 裁决: 驳回。理由: {review_result.get('justification')}")
                return review_result

            # 如果是事实性矛盾，启动阶段2
            logging.info(f"    [Agent3] 裁决: 确认为事实性矛盾。理由: {review_result.get('justification')}")
            logging.info(f"    [Agent3] 阶段2: 移交Agent4进行相关性仲裁。")

            # 阶段2: 调用Agent4进行相关性检查
            relevance_result = self.agent4.run(conflict_reason=reason, rule_text=rule_text)
            
            # 将Agent4的结果包装成Agent3的输出格式，返回给Agent2
            final_decision = {
                "is_true_conflict": relevance_result.get("is_relevant_conflict"),
                "justification": relevance_result.get("justification")
            }
            status = "确认相关" if final_decision["is_true_conflict"] else "判定为不相关"
            logging.info(f"    [Agent4] 最终裁决: {status}。理由: {final_decision['justification']}")
            return final_decision

        except Exception as e:
            logging.error(f"    [Agent3] 审查过程中发生严重错误: {e}。默认驳回该冲突。")
            return {"is_true_conflict": False, "justification": f"Agent3审查链调用失败: {e}"}