import logging
import json
from typing import Dict
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.language_models.chat_models import BaseChatModel
from rule_definition_finder import RuleDefinitionFinderTool

class RelevanceCheckResult(BaseModel):
    """定义了相关性检查结果的数据结构。"""
    is_relevant_conflict: bool = Field(
        description="在与'规则权威定义'严格比对后，这个事实性矛盾是否与定义直接相关？"
    )
    justification: str = Field(
        description="解释你的判断。例如：'相关，因为冲突点（等待期天数）是规则定义的核心要素。'或'不相关，因为冲突点（缴费银行）未在规则定义中提及。'"
    )

class RelevanceCheckerAgent:
    """
    Agent4: 相关性仲裁员。
    职责：判断一个【已被确认为事实性矛盾】的冲突点，是否落在【规则的权威定义】范围之内。
    """

    RELEVANCE_PROMPT = """
你是一名规则仲裁专家，你的任务是进行最终的相关性裁决。

【背景】
一个下级审计团队已经确认了以下【事实性矛盾】。现在需要你来判断这个矛盾是否与【规则的权威定义】相关。

- **规则核心概念**: "{rule_text}"
- **已确认的事实矛盾**: "{conflict_reason}"

【权威依据】
这是你唯一的判断标准。
- **规则权威定义**: 
---
{rule_definition}
---

【你的仲裁任务】
你的唯一任务是：判断上述【已确认的事实矛盾】所描述的问题，是否属于【规则权威定义】所明确提到的？不许擅自根据规则及其定义文字进行随意扩展联想。严格遵循【规则权威定义】进行判断。

- **如果相关**: 意味着这个矛盾点是本次审计需要关注的核心问题。
- **如果不相关**: 意味着虽然这是一个事实矛盾，但它超出了当前规则的审计范围，应在其他规则下处理。

请以指定的JSON格式返回你的最终仲裁结果。

{format_instructions}
"""

    def __init__(self, llm_instance: BaseChatModel, definition_finder: RuleDefinitionFinderTool):
        """
        初始化相关性仲裁Agent。
        Args:
            llm_instance (BaseChatModel): LLM实例。
            definition_finder (RuleDefinitionFinderTool): 用于查找规则定义的工具。
        """
        parser = JsonOutputParser(pydantic_object=RelevanceCheckResult)
        prompt = ChatPromptTemplate.from_template(
            template=self.RELEVANCE_PROMPT,
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        self.relevance_chain = prompt | llm_instance | parser
        self.definition_finder = definition_finder
        logging.info("Agent4: RelevanceCheckerAgent 初始化完成。")

    def run(self, conflict_reason: str, rule_text: str) -> Dict:
        """
        执行相关性检查。
        Args:
            conflict_reason (str): Agent3确认的事实性矛盾理由。
            rule_text (str): 当前审查的规则核心概念。
        Returns:
            Dict: 包含 'is_relevant_conflict' 和 'justification' 的字典。
        """
        logging.info(f"    [Agent4] 正在检查冲突 '{conflict_reason}' 与规则 '{rule_text}' 的相关性...")

        # 获取权威定义
        try:
            tool_input = json.dumps({"core_concept": rule_text})
            rule_definition = self.definition_finder._run(tool_input)
        except Exception as e:
            logging.error(f"    [Agent4] 查找规则定义时出错: {e}。默认判定为不相关。")
            return {"is_relevant_conflict": False, "justification": f"查找规则定义失败: {e}"}

        # 调用LLM进行判断
        input_data = {
            "conflict_reason": conflict_reason,
            "rule_text": rule_text,
            "rule_definition": rule_definition
        }
        try:
            result = self.relevance_chain.invoke(input_data)
            return result.dict() if isinstance(result, BaseModel) else result
        except Exception as e:
            logging.error(f"    [Agent4] 相关性检查链调用失败: {e}。默认判定为不相关。")
            return {"is_relevant_conflict": False, "justification": f"LLM调用失败: {e}"}