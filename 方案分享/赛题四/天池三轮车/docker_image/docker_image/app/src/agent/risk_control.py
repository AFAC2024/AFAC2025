from typing import Any, List, Optional

from pydantic import Field

from src.agent.mcp import MCPAgent
from src.prompt.mcp import NEXT_STEP_PROMPT_ZN
from src.prompt.risk_control import RISK_SYSTEM_PROMPT
from src.schema import Message
from src.tool import Terminate, ToolCollection
from src.tool.risk_control import RiskControlTool


class RiskControlAgent(MCPAgent):
    """Risk analysis agent focused on identifying and quantifying investment risks."""

    name: str = "risk_control_agent"
    description: str = "Analyzes financial risks and proposes risk control strategies for stock investments."
    system_prompt: str = RISK_SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT_ZN

    # Initialize with FinGenius tools with proper type annotation
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            RiskControlTool(),
            Terminate(),
        )
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    async def run(
        self, request: Optional[str] = None, stock_code: Optional[str] = None
    ) -> Any:
        """Run risk analysis on the given stock.

        Args:
            request: Optional initial request to process. If provided, overrides stock_code parameter.
            stock_code: The stock code/ticker to analyze

        Returns:
            Dictionary containing comprehensive risk analysis
        """
        # If stock_code is provided but request is not, create request from stock_code
        if stock_code and not request:
            # Set up system message about the stock being analyzed
            self.memory.add_message(
                Message.system_message(
                    f"你正在分析股票 {stock_code} 的风险因素。请收集相关财务数据并进行全面风险评估。"
                )
            )
            request = f"请对 {stock_code} 进行全面的风险分析。"

        # Call parent implementation with the request
        return await super().run(request)
