from typing import Any, List, Optional
from pydantic import Field

from src.agent.mcp import MCPAgent
from src.prompt.big_deal_analysis import BIG_DEAL_SYSTEM_PROMPT
from src.prompt.mcp import NEXT_STEP_PROMPT_ZN
from src.schema import Message
from src.tool import Terminate, ToolCollection
from src.tool.big_deal_analysis import BigDealAnalysisTool


class BigDealAnalysisAgent(MCPAgent):
    """大单异动分析 Agent"""

    name: str = "big_deal_analysis_agent"
    description: str = "分析市场及个股大单资金异动，为投资决策提供依据。"

    system_prompt: str = BIG_DEAL_SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT_ZN

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            BigDealAnalysisTool(),
            Terminate(),
        )
    )
    # 限制单次观察字符，防止内存过大导致 LLM 无法响应
    max_observe: int = 10000
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    async def run(
        self,
        request: Optional[str] = None,
        stock_code: Optional[str] = None,
    ) -> Any:
        """Run big deal analysis"""
        if stock_code and not request:
            self.memory.add_message(
                Message.system_message(
                    f"你正在分析股票 {stock_code} 的大单资金流向，请综合资金异动与价格走势给出结论。"
                )
            )
            request = f"请对 {stock_code} 进行大单异动深度分析，并生成投资建议。"

        return await super().run(request) 