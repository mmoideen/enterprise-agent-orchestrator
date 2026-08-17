"""MCP server implementation for exposing agent capabilities as tools."""

from typing import Any, Callable

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()


class ToolDefinition(BaseModel):
    """MCP tool definition schema."""

    name: str
    description: str
    inputSchema: dict[str, Any]


class ToolInvocationRequest(BaseModel):
    """Request body for tool invocation."""

    arguments: dict[str, Any]


class MCPServer:
    """
    MCP server for exposing agent capabilities as standardized tools.

    This server implements the Model Context Protocol, allowing agents
    to be consumed as tools by other systems. It handles tool registration,
    discovery, and invocation routing.
    """

    def __init__(self, app: FastAPI) -> None:
        """
        Initialize the MCP server.

        Args:
            app: FastAPI application to mount routes on.
        """
        self.app = app
        self.tools: dict[str, dict[str, Any]] = {}
        self._register_routes()

    def _register_routes(self) -> None:
        """Register MCP protocol routes."""

        @self.app.get("/tools")
        async def list_tools() -> dict[str, list[dict[str, Any]]]:
            """List all available tools."""
            tools_list = [
                {
                    "name": name,
                    "description": tool["description"],
                    "inputSchema": tool["input_schema"],
                }
                for name, tool in self.tools.items()
            ]
            return {"tools": tools_list}

        @self.app.post("/tools/{tool_name}/invoke")
        async def invoke_tool(
            tool_name: str, request: ToolInvocationRequest
        ) -> dict[str, Any]:
            """Invoke a specific tool."""
            if tool_name not in self.tools:
                raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

            tool = self.tools[tool_name]
            handler = tool["handler"]

            try:
                result = await handler(request.arguments)
                logger.info(
                    "tool_invoked",
                    tool_name=tool_name,
                    arguments=request.arguments,
                )
                return {"result": result}

            except Exception as e:
                logger.error(
                    "tool_invocation_error",
                    tool_name=tool_name,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Tool invocation failed: {str(e)}",
                )

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        """
        Register a new tool with the MCP server.

        Args:
            name: Tool name (unique identifier).
            description: Human-readable tool description.
            input_schema: JSON schema for tool input parameters.
            handler: Async function that handles tool invocation.
        """
        if name in self.tools:
            raise ValueError(f"Tool '{name}' is already registered")

        self.tools[name] = {
            "description": description,
            "input_schema": input_schema,
            "handler": handler,
        }

        logger.info(
            "tool_registered",
            tool_name=name,
        )

    def unregister_tool(self, name: str) -> None:
        """
        Unregister a tool from the MCP server.

        Args:
            name: Tool name to unregister.
        """
        if name in self.tools:
            del self.tools[name]
            logger.info(
                "tool_unregistered",
                tool_name=name,
            )
