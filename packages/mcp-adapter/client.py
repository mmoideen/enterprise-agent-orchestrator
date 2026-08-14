"""MCP client for agent tool access."""

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class MCPTool:
    """Represents an MCP tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]
    server_url: str


class MCPClient:
    """
    Client for interacting with MCP servers.

    This client provides a standardized interface for agents to discover
    and invoke tools exposed by MCP servers. It handles connection management,
    request/response formatting, and error handling.
    """

    def __init__(self, timeout: int = 30) -> None:
        """
        Initialize the MCP client.

        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout
        self.http_client = httpx.AsyncClient(timeout=timeout)
        self._tools_cache: dict[str, list[MCPTool]] = {}

    async def discover_tools(self, server_url: str) -> list[MCPTool]:
        """
        Discover available tools from an MCP server.

        Args:
            server_url: Base URL of the MCP server.

        Returns:
            List of available MCPTool objects.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        if server_url in self._tools_cache:
            return self._tools_cache[server_url]

        try:
            response = await self.http_client.get(f"{server_url}/tools")
            response.raise_for_status()

            tools_data = response.json()
            tools = [
                MCPTool(
                    name=tool["name"],
                    description=tool["description"],
                    input_schema=tool["inputSchema"],
                    server_url=server_url,
                )
                for tool in tools_data.get("tools", [])
            ]

            self._tools_cache[server_url] = tools
            logger.info(
                "discovered_mcp_tools",
                server_url=server_url,
                tool_count=len(tools),
            )

            return tools

        except httpx.HTTPError as e:
            logger.error(
                "mcp_discovery_failed",
                server_url=server_url,
                error=str(e),
            )
            raise

    async def invoke_tool(
        self, tool: MCPTool, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Invoke an MCP tool with the given arguments.

        Args:
            tool: MCPTool to invoke.
            arguments: Tool input arguments.

        Returns:
            Tool execution result.

        Raises:
            httpx.HTTPError: If the request fails.
            ValueError: If arguments don't match the tool schema.
        """
        # Validate arguments against schema (basic validation)
        # In production, use jsonschema for full validation
        required_params = tool.input_schema.get("required", [])
        missing_params = set(required_params) - set(arguments.keys())

        if missing_params:
            raise ValueError(
                f"Missing required parameters: {missing_params}"
            )

        try:
            response = await self.http_client.post(
                f"{tool.server_url}/tools/{tool.name}/invoke",
                json={"arguments": arguments},
            )
            response.raise_for_status()

            result = response.json()
            logger.info(
                "mcp_tool_invoked",
                tool_name=tool.name,
                server_url=tool.server_url,
            )

            return result

        except httpx.HTTPError as e:
            logger.error(
                "mcp_tool_invocation_failed",
                tool_name=tool.name,
                error=str(e),
            )
            raise

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        await self.http_client.aclose()

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
