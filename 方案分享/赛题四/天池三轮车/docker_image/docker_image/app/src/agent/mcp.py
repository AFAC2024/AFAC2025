from typing import Any, Dict, List, Optional, Tuple

from pydantic import Field, field_validator

from src.agent.toolcall import ToolCallAgent
from src.config import config
from src.logger import logger
from src.prompt.mcp import MULTIMEDIA_RESPONSE_PROMPT, NEXT_STEP_PROMPT, SYSTEM_PROMPT
from src.schema import Message
from src.tool.base import ToolResult


class MCPAgent(ToolCallAgent):
    """Agent for interacting with MCP (Model Context Protocol) servers.

    This agent connects to one or more MCP servers using either SSE or stdio transport
    and makes the servers' tools available through the agent's tool interface.
    """

    name: str = "mcp_agent"
    description: str = "An agent that connects to MCP servers and uses their tools."
    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    # Configuration values
    max_steps: int = Field(default=10)
    max_observe: int = Field(default=10000)
    refresh_tools_interval: int = Field(
        default=5, description="Refresh tools every N steps"
    )

    # MCP client and tools
    mcp_clients: Any = Field(default=None)
    available_tools: Optional[Any] = Field(
        default=None, description="Will be set in initialize()"
    )

    # State tracking
    tool_schemas: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    special_tool_names: List[str] = Field(default=["terminate"])
    connected_servers: Dict[str, str] = Field(
        default_factory=dict, description="server_id -> url/command mapping"
    )
    initialized: bool = Field(default=False)

    @classmethod
    @field_validator("mcp_clients", mode="before")
    def init_mcp_clients(cls, v: Any) -> Any:
        """Initialize MCPClients if not provided."""
        if v is None:
            from src.tool.mcp_client import MCPClients

            return MCPClients()
        return v

    @classmethod
    async def create(cls, **kwargs) -> "MCPAgent":
        """Factory method to create and properly initialize an MCPAgent instance."""
        instance = cls(**kwargs)
        try:
            await instance.initialize_mcp_servers()
        except Exception as e:
            logger.warning(
                f"Failed to initialize MCP servers: {str(e)}. Continuing with local tools only."
            )

        instance.initialized = True

        # Set available_tools to our MCP instance if not already set
        if instance.available_tools is None:
            instance.available_tools = instance.mcp_clients

        # Add system message about available tools only if we have MCP clients
        if instance.mcp_clients and hasattr(instance.mcp_clients, "tool_map"):
            tool_names = list(instance.mcp_clients.tool_map.keys())
            instance.memory.add_message(
                Message.system_message(
                    f"{instance.system_prompt}\n\nAvailable MCP tools: {', '.join(tool_names)}"
                )
            )

        return instance

    async def initialize_mcp_servers(self) -> None:
        """Initialize connections to configured MCP servers."""
        for server_id, server_config in config.mcp_config.servers.items():
            try:
                if server_config.type == "sse" and server_config.url:
                    await self.connect_mcp_server(server_config.url, server_id)
                    logger.info(
                        f"Connected to MCP server {server_id} at {server_config.url}"
                    )
                elif server_config.type == "stdio" and server_config.command:
                    await self.connect_mcp_server(
                        server_config.command,
                        server_id,
                        use_stdio=True,
                        stdio_args=server_config.args,
                    )
                    logger.info(
                        f"Connected to MCP server {server_id} using command {server_config.command}"
                    )
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server_id}: {e}")

    async def connect_mcp_server(
        self,
        server_url: str,
        server_id: str = "",
        use_stdio: bool = False,
        stdio_args: Optional[List[str]] = None,
    ) -> None:
        """Connect to an MCP server and add its tools."""
        if use_stdio:
            await self.mcp_clients.connect_stdio(
                server_url, stdio_args or [], server_id
            )
        else:
            await self.mcp_clients.connect_sse(server_url, server_id)

        self.connected_servers[server_id or server_url] = server_url

        # Add tools if needed
        if self.available_tools and self.available_tools is not self.mcp_clients:
            new_tools = [
                tool for tool in self.mcp_clients.tools if tool.server_id == server_id
            ]
            self.available_tools.add_tools(*new_tools)

        # Refresh tool schemas
        await self._refresh_tools()

    async def disconnect_mcp_server(self, server_id: str = "") -> None:
        """Disconnect from an MCP server and remove its tools."""
        if not self.mcp_clients:
            return

        await self.mcp_clients.disconnect(server_id)

        if server_id:
            self.connected_servers.pop(server_id, None)
        else:
            self.connected_servers.clear()

        # Rebuild available_tools if needed
        if self.available_tools and self.available_tools is not self.mcp_clients:
            from src.tool.mcp_client import MCPClientTool

            base_tools = [
                tool
                for tool in self.available_tools.tools
                if not isinstance(tool, MCPClientTool)
            ]

            remaining_mcp_tools = [
                tool
                for tool in self.mcp_clients.tools
                if hasattr(tool, "server_id")
                and tool.server_id in self.connected_servers
            ]

            self.available_tools.tools = base_tools
            self.available_tools.add_tools(*remaining_mcp_tools)

    async def initialize(
        self,
        connection_type: Optional[str] = None,
        server_url: Optional[str] = None,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        server_id: str = "",
    ) -> None:
        """Initialize a single MCP connection."""
        # Allow initialization without connection parameters (use configured servers)
        if connection_type is None:
            if not self.initialized:
                await self.initialize_mcp_servers()
        elif connection_type == "sse":
            if not server_url:
                raise ValueError("Server URL is required for SSE connection")
            await self.connect_mcp_server(server_url=server_url, server_id=server_id)
        elif connection_type == "stdio":
            if not command:
                raise ValueError("Command is required for stdio connection")
            await self.connect_mcp_server(
                server_url=command,
                server_id=server_id,
                use_stdio=True,
                stdio_args=args or [],
            )
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")

        # Set available_tools if needed
        if self.available_tools is None:
            self.available_tools = self.mcp_clients

        await self._refresh_tools()
        self.initialized = True

    async def _refresh_tools(self) -> Tuple[List[str], List[str]]:
        """Refresh the list of available tools from the MCP server."""
        if not self.mcp_clients or not self.mcp_clients.sessions:
            return [], []

        # Get current tool schemas
        response = await self.mcp_clients.sessions.list_tools()
        current_tools = {tool.name: tool.inputSchema for tool in response.tools}

        # Determine changes
        current_names = set(current_tools.keys())
        previous_names = set(self.tool_schemas.keys())

        added_tools = list(current_names - previous_names)
        removed_tools = list(previous_names - current_names)

        # Check for schema changes
        changed_tools = [
            name
            for name in current_names.intersection(previous_names)
            if current_tools[name] != self.tool_schemas.get(name)
        ]

        # Update stored schemas
        self.tool_schemas = current_tools

        # Log and notify about changes
        if added_tools:
            logger.info(f"Added MCP tools: {added_tools}")
            self.memory.add_message(
                Message.system_message(f"New tools available: {', '.join(added_tools)}")
            )

        if removed_tools:
            logger.info(f"Removed MCP tools: {removed_tools}")
            self.memory.add_message(
                Message.system_message(
                    f"Tools no longer available: {', '.join(removed_tools)}"
                )
            )

        if changed_tools:
            logger.info(f"Changed MCP tools: {changed_tools}")

        return added_tools, removed_tools

    async def think(self) -> bool:
        """Process current state and decide next action."""
        # Initialize if not already done
        if not self.initialized:
            await self.initialize_mcp_servers()
            self.initialized = True

        # Periodically refresh tools if mcp_clients exists
        if (
            self.mcp_clients
            and self.current_step % self.refresh_tools_interval == 0
            and self.mcp_clients.sessions
        ):
            await self._refresh_tools()
            if self.mcp_clients.sessions and not self.mcp_clients.tool_map:
                logger.info("MCP service has shut down")

        return await super().think()

    async def _handle_special_tool(self, name: str, result: Any, **kwargs) -> None:
        """Handle special tool execution and state changes"""
        await super()._handle_special_tool(name, result, **kwargs)

        # Handle multimedia responses
        if isinstance(result, ToolResult) and result.base64_image:
            self.memory.add_message(
                Message.system_message(
                    MULTIMEDIA_RESPONSE_PROMPT.format(tool_name=name)
                )
            )

    def _should_finish_execution(self, name: str, **kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return name.lower() == "terminate"

    async def cleanup(self) -> None:
        """Clean up MCP connection when done."""
        if self.initialized and self.mcp_clients:
            await self.disconnect_mcp_server()
            self.initialized = False
            logger.info("MCP connections closed")
