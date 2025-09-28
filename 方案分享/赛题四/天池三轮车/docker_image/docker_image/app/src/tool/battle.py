from typing import Any, Dict, Optional

from pydantic import Field

from src.tool.base import BaseTool, ToolFailure, ToolResult


class Battle(BaseTool):
    """Tool for agents to interact in the battle environment."""

    name: str = "battle"
    description: str = "在对战环境中进行互动的工具。您可以发表观点和/或投票。"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "vote": {
                "type": "string",
                "enum": ["bullish", "bearish"],
                "description": "您对股票走势的最终投票。'bullish'表示看涨，'bearish'表示看跌。",
            },
            "speak": {
                "type": "string",
                "description": "您想与其他智能体分享的观点内容。",
            },
        },
        "required": ["vote", "speak"],
    }

    agent_id: str = Field(..., description="The ID of the agent using this tool")
    controller: Optional[Any] = Field(default=None)

    async def execute(
        self, speak: Optional[str] = None, vote: Optional[str] = None
    ) -> ToolResult:
        """
        Execute the battle action with speaking and/or voting
        """
        if not self.controller:
            return ToolFailure(error="对战环境未初始化")

        result = None
        formatted_output = ""

        # Validate vote if provided
        if vote is not None:
            if vote.lower() not in ["bullish", "bearish"]:
                return ToolFailure(error="投票必须是'bullish'(看涨)或'bearish'(看跌)")
            vote = vote.lower()

        # Handle speaking and voting
        if speak is not None and speak.strip():
            # Format the output as: AgentName[vote content]: speak content
            formatted_output = f"{self.agent_id}[{vote if vote else '未投票'}]: {speak}"

            # Handle the actual speak action
            result = await self.controller.handle_speak(self.agent_id, speak)
            if result.error:
                return result

        # Handle voting if vote is provided
        if vote is not None:
            result = await self.controller.handle_vote(self.agent_id, vote)

            # If there was no speak content, create a formatted output for just the vote
            if not formatted_output:
                formatted_output = f"{self.agent_id}[{vote}]: "

        # If neither speak nor vote was provided
        if result is None:
            return ToolFailure(error="您必须提供发言内容和投票选项")

        # Update the result output with the formatted display
        if result.output is None:
            result.output = formatted_output
        else:
            result.output = formatted_output

        return result
