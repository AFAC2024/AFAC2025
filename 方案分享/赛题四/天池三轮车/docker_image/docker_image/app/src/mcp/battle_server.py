from src.mcp.server import MCPServer
from src.tool import Battle, Terminate


class BattleServer(MCPServer):
    def __init__(self, name: str = "BattleServer"):
        super().__init__(name)

    def _initialize_standard_tools(self) -> None:
        self.tools.update(
            {
                "terminate": Terminate(),
                "battle": Battle(),
            }
        )
