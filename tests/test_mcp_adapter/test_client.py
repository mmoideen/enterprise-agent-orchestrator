"""Tests for the MCP client."""

from typing import Any

import httpx
import pytest

from packages.mcp_adapter.client import MCPClient, MCPTool

SERVER_URL = "http://mcp.test"

TOOL = MCPTool(
    name="lookup_employee",
    description="Look up an employee record",
    input_schema={"required": ["employee_id"]},
    server_url=SERVER_URL,
)


def _client(handler: Any) -> MCPClient:
    """Build an MCP client backed by a mock transport."""
    client = MCPClient()
    client.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


class TestToolDiscovery:
    """Tests for discovering tools from an MCP server."""

    @pytest.mark.asyncio
    async def test_discover_tools_and_cache(self) -> None:
        """Test that discovery parses tools and serves repeat calls from cache."""
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(str(request.url))
            return httpx.Response(
                200,
                json={
                    "tools": [
                        {
                            "name": "lookup_employee",
                            "description": "Look up an employee record",
                            "inputSchema": {"required": ["employee_id"]},
                        }
                    ]
                },
            )

        async with _client(handler) as client:
            tools = await client.discover_tools(SERVER_URL)
            cached = await client.discover_tools(SERVER_URL)

        assert len(tools) == 1
        assert tools[0].name == "lookup_employee"
        assert tools[0].server_url == SERVER_URL
        assert cached == tools
        assert calls == [f"{SERVER_URL}/tools"]

    @pytest.mark.asyncio
    async def test_discover_tools_propagates_http_error(self) -> None:
        """Test that a failing discovery request is raised to the caller."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"detail": "boom"})

        async with _client(handler) as client:
            with pytest.raises(httpx.HTTPError):
                await client.discover_tools(SERVER_URL)


class TestToolInvocation:
    """Tests for invoking tools on an MCP server."""

    @pytest.mark.asyncio
    async def test_invoke_tool_success(self) -> None:
        """Test a successful tool invocation returns the server payload."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/tools/lookup_employee/invoke"
            return httpx.Response(200, json={"result": {"employee_id": "e-1"}})

        async with _client(handler) as client:
            result = await client.invoke_tool(TOOL, {"employee_id": "e-1"})

        assert result == {"result": {"employee_id": "e-1"}}

    @pytest.mark.asyncio
    async def test_invoke_tool_missing_required_argument(self) -> None:
        """Test that missing schema-required arguments are rejected locally."""

        def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
            raise AssertionError("request should not be sent")

        async with _client(handler) as client:
            with pytest.raises(ValueError, match="Missing required parameters"):
                await client.invoke_tool(TOOL, {})

    @pytest.mark.asyncio
    async def test_invoke_tool_propagates_http_error(self) -> None:
        """Test that a failing invocation is raised to the caller."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"detail": "unavailable"})

        async with _client(handler) as client:
            with pytest.raises(httpx.HTTPError):
                await client.invoke_tool(TOOL, {"employee_id": "e-1"})
