from pydantic import Field

from src.agent.mcp import MCPAgent
from src.prompt.mcp import NEXT_STEP_PROMPT_ZN
from src.prompt.report import REPORT_SYSTEM_PROMPT
from src.tool import Terminate, ToolCollection
from src.tool.create_html import CreateHtmlTool


class ReportAgent(MCPAgent):
    """Report generation agent that synthesizes insights from other agents."""

    name: str = "report_agent"
    description: str = "Generates comprehensive reports by synthesizing insights from other specialized agents."
    system_prompt: str = REPORT_SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT_ZN

    # Initialize with FinGenius tools and proper type annotation
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            CreateHtmlTool(),
            Terminate(),
        )
    )
    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])


if __name__ == "__main__":
    import asyncio

    async def run_agent():
        agent = await ReportAgent.create()
        await agent.initialize()
        prompt = "生成一个关于AI的报告 html格式"
        await agent.run(prompt)

    asyncio.run(run_agent())
