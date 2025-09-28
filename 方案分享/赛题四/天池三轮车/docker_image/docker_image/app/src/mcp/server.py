import argparse
import asyncio
import atexit
import json
import logging
import sys
from inspect import Parameter, Signature
from typing import Any, Dict, Optional

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.routing import Mount, Route

from mcp.server import FastMCP, Server
from mcp.server.sse import SseServerTransport
from src.logger import logger
from src.tool import BaseTool, Terminate


logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stderr)])


class MCPServer:
    """MCP Server implementation with tool registration and management."""

    def __init__(self, name: str = "FinGenius"):
        self.server = FastMCP(name)
        self.tools: Dict[str, BaseTool] = {}

        # Initialize standard tools
        self._initialize_standard_tools()

    def _initialize_standard_tools(self) -> None:
        """Initialize standard tools available in the server."""
        self.tools.update(
            {
                "terminate": Terminate(),
            }
        )

    def register_tool(self, tool: BaseTool, method_name: Optional[str] = None) -> None:
        """Register a tool with parameter validation and documentation."""
        tool_name = method_name or tool.name
        tool_param = tool.to_param()
        tool_function = tool_param["function"]

        # Define the async function to be registered
        async def tool_method(**kwargs):
            logger.info(f"Executing {tool_name}: {kwargs}")
            result = await tool.execute(**kwargs)

            logger.info(f"Result of {tool_name}: {result}")

            # Handle different types of results (match original logic)
            if hasattr(result, "model_dump"):
                return json.dumps(result.model_dump())
            elif isinstance(result, dict):
                return json.dumps(result)
            return result

        # Set method metadata
        tool_method.__name__ = tool_name
        tool_method.__doc__ = self._build_docstring(tool_function)
        tool_method.__signature__ = self._build_signature(tool_function)

        # Store parameter schema (important for tools that access it programmatically)
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])
        tool_method._parameter_schema = {
            param_name: {
                "description": param_details.get("description", ""),
                "type": param_details.get("type", "any"),
                "required": param_name in required_params,
            }
            for param_name, param_details in param_props.items()
        }

        # Register with server
        self.server.tool()(tool_method)
        logger.info(f"Registered tool: {tool_name}")

    def _build_docstring(self, tool_function: dict) -> str:
        """Build a formatted docstring from tool function metadata."""
        description = tool_function.get("description", "")
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])

        # Build docstring (match original format)
        docstring = description
        if param_props:
            docstring += "\n\nParameters:\n"
            for param_name, param_details in param_props.items():
                required_str = (
                    "(required)" if param_name in required_params else "(optional)"
                )
                param_type = param_details.get("type", "any")
                param_desc = param_details.get("description", "")
                docstring += (
                    f"    {param_name} ({param_type}) {required_str}: {param_desc}\n"
                )

        return docstring

    def _build_signature(self, tool_function: dict) -> Signature:
        """Build a function signature from tool function metadata."""
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])

        parameters = []

        # Follow original type mapping
        for param_name, param_details in param_props.items():
            param_type = param_details.get("type", "")
            default = Parameter.empty if param_name in required_params else None

            # Map JSON Schema types to Python types (same as original)
            annotation = Any
            if param_type == "string":
                annotation = str
            elif param_type == "integer":
                annotation = int
            elif param_type == "number":
                annotation = float
            elif param_type == "boolean":
                annotation = bool
            elif param_type == "object":
                annotation = dict
            elif param_type == "array":
                annotation = list

            # Create parameter with same structure as original
            param = Parameter(
                name=param_name,
                kind=Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation,
            )
            parameters.append(param)

        return Signature(parameters=parameters)

    async def cleanup(self) -> None:
        """Clean up server resources."""
        logger.info("Cleaning up resources")
        # Follow original cleanup logic - only clean browser tool
        if "browser" in self.tools and hasattr(self.tools["browser"], "cleanup"):
            await self.tools["browser"].cleanup()

    def register_all_tools(self) -> None:
        """Register all tools with the server."""
        for tool in self.tools.values():
            self.register_tool(tool)

    def run(self, transport: str = "stdio") -> None:
        """Run the MCP server."""
        # Register all tools
        self.register_all_tools()

        # Register cleanup function (match original behavior)
        atexit.register(lambda: asyncio.run(self.cleanup()))

        # Start server (with same logging as original)
        logger.info(f"Starting FinGenius server ({transport} mode)")
        self.server.run(transport=transport)


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    # Set up CORS middleware to allow connections from any origin
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        )
    ]

    # Use '/messages/' as the endpoint path for SSE connections
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        try:
            logger.info(f"SSE connection request received from {request.client}")
            async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
            ) as (read_stream, write_stream):
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options(),
                )
        except Exception as e:
            logger.error(f"Error handling SSE connection: {str(e)}")
            raise

    # Create Starlette app with middleware and routes
    app = Starlette(
        debug=debug,
        middleware=middleware,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    # Add a health check endpoint
    @app.route("/health")
    async def health_check(request: Request):
        from starlette.responses import JSONResponse

        return JSONResponse(
            {
                "status": "ok",
                "message": "FinGenius server is running",
            }
        )

    return app


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="FinGenius MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Communication method: stdio or sse (default: stdio)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (for sse)")
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to listen on (for sse)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.transport == "sse":
        # Create an instance of MCPServer
        mcp_server = MCPServer()
        # Register all tools
        mcp_server.register_all_tools()
        # Get the underlying mcp_server from FastMCP
        underlying_server = mcp_server.server._mcp_server  # noqa: WPS437

        logger.info(f"Starting FinGenius server with SSE on {args.host}:{args.port}")

        # Create Starlette application
        starlette_app = create_starlette_app(underlying_server, debug=args.debug)

        # Run with uvicorn
        uvicorn.run(
            starlette_app,
            host=args.host,
            port=args.port,
            log_level="info",
            access_log=True,
        )
    else:
        # Run in stdio mode
        mcp_server = MCPServer()
        mcp_server.run(transport=args.transport)
