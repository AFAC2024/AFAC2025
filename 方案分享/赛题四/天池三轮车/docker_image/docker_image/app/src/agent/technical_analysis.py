from typing import Any, List, Optional

from pydantic import Field

from src.agent.mcp import MCPAgent
from src.prompt.mcp import NEXT_STEP_PROMPT_ZN
from src.prompt.technical_analysis import TECHNICAL_ANALYSIS_SYSTEM_PROMPT
from src.schema import Message
from src.tool import Terminate, ToolCollection
from src.tool.technical_analysis import TechnicalAnalysisTool


class TechnicalAnalysisAgent(MCPAgent):
    """Technical analysis agent applying technical indicators to stock analysis."""

    name: str = "technical_analysis_agent"
    description: str = (
        "Applies technical analysis and chart patterns to stock market analysis."
    )

    system_prompt: str = TECHNICAL_ANALYSIS_SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT_ZN

    # Initialize with FinGenius tools with proper type annotation
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            TechnicalAnalysisTool(),
            Terminate(),
        )
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    async def run(
        self, request: Optional[str] = None, stock_code: Optional[str] = None
    ) -> Any:
        """Run technical analysis on the given stock using technical indicators.

        Args:
            request: Optional initial request to process. If provided, overrides stock_code parameter.
            stock_code: The stock code/ticker to analyze

        Returns:
            Dictionary containing technical analysis insights
        """
        # If stock_code is provided but request is not, create request from stock_code
        if stock_code and not request:
            # Set up system message about the stock being analyzed
            self.memory.add_message(
                Message.system_message(
                    f"你正在对股票 {stock_code} 进行技术面分析。请评估价格走势、图表形态和关键技术指标，形成短中期交易策略。"
                )
            )
            request = f"请分析 {stock_code} 的技术指标和图表形态。"

        # Call parent implementation with the request
        return await super().run(request)
