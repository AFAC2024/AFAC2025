from typing import Any, List, Optional

from pydantic import Field

from src.agent.mcp import MCPAgent
from src.prompt.chip_analysis import CHIP_ANALYSIS_SYSTEM_PROMPT
from src.prompt.mcp import NEXT_STEP_PROMPT_ZN
from src.schema import Message
from src.tool import Terminate, ToolCollection
from src.tool.chip_analysis import ChipAnalysisTool


class ChipAnalysisAgent(MCPAgent):
    """筹码分析agent，专注于股票筹码分布和技术分析"""

    name: str = "chip_analysis_agent"
    description: str = (
        "专业的筹码分析师，擅长分析股票筹码分布、主力行为、散户情绪和A股特色筹码技术分析"
    )

    system_prompt: str = CHIP_ANALYSIS_SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT_ZN

    # Initialize with FinGenius tools with proper type annotation
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            ChipAnalysisTool(),
            Terminate(),
        )
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    async def run(
        self, request: Optional[str] = None, stock_code: Optional[str] = None
    ) -> Any:
        """运行筹码分析，分析指定股票的筹码分布和技术指标

        Args:
            request: Optional initial request to process. If provided, overrides stock_code parameter.
            stock_code: The stock code/ticker to analyze

        Returns:
            Dictionary containing comprehensive chip analysis results
        """
        # If stock_code is provided but request is not, create request from stock_code
        if stock_code and not request:
            # Set up system message about the stock being analyzed
            self.memory.add_message(
                Message.system_message(
                    f"你正在分析股票 {stock_code} 的筹码分布。请使用筹码分析工具获取筹码分布数据，并进行全面的筹码技术分析，包括主力成本、套牢区、集中度等关键指标。"
                )
            )
            request = f"请对 {stock_code} 进行全面的筹码分析，包括筹码分布、主力行为、散户情绪和交易建议。"

        # Call parent implementation with the request
        return await super().run(request) 