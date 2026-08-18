"""Tests for the MCP server."""

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from packages.mcp_adapter.server import MCPServer

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"employee_id": {"type": "string"}},
    "required": ["employee_id"],
}


async def _echo(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return the arguments it was called with."""
    return {"echo": arguments}


async def _boom(arguments: dict[str, Any]) -> dict[str, Any]:
    """Fail to exercise the error path."""
    raise RuntimeError("handler exploded")


@pytest.fixture
def server() -> MCPServer:
    """Create an MCP server with a single registered tool."""
    mcp_server = MCPServer(FastAPI())
    mcp_server.register_tool(
        name="lookup_employee",
        description="Look up an employee record",
        input_schema=INPUT_SCHEMA,
        handler=_echo,
    )
    return mcp_server


class TestToolRegistration:
    """Tests for the tool registry."""

    def test_duplicate_registration_rejected(self, server: MCPServer) -> None:
        """Test that registering the same tool name twice fails."""
        with pytest.raises(ValueError, match="already registered"):
            server.register_tool(
                name="lookup_employee",
                description="Duplicate",
                input_schema=INPUT_SCHEMA,
                handler=_echo,
            )

    def test_unregister_tool(self, server: MCPServer) -> None:
        """Test that unregistering removes the tool and is idempotent."""
        server.unregister_tool("lookup_employee")
        server.unregister_tool("lookup_employee")

        assert server.tools == {}


class TestProtocolRoutes:
    """Tests for the MCP HTTP surface."""

    @pytest.mark.asyncio
    async def test_list_tools(self, server: MCPServer) -> None:
        """Test that registered tools are advertised with their schema."""
        transport = ASGITransport(app=server.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/tools")

        assert response.status_code == 200
        assert response.json() == {
            "tools": [
                {
                    "name": "lookup_employee",
                    "description": "Look up an employee record",
                    "inputSchema": INPUT_SCHEMA,
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_invoke_tool(self, server: MCPServer) -> None:
        """Test that invocation routes to the registered handler."""
        transport = ASGITransport(app=server.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/tools/lookup_employee/invoke",
                json={"arguments": {"employee_id": "e-1"}},
            )

        assert response.status_code == 200
        assert response.json() == {"result": {"echo": {"employee_id": "e-1"}}}

    @pytest.mark.asyncio
    async def test_invoke_unknown_tool(self, server: MCPServer) -> None:
        """Test that unknown tools return 404."""
        transport = ASGITransport(app=server.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/tools/missing/invoke", json={"arguments": {}})

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invoke_tool_handler_failure(self, server: MCPServer) -> None:
        """Test that handler failures surface as 500 responses."""
        server.register_tool(
            name="explode",
            description="Always fails",
            input_schema={},
            handler=_boom,
        )

        transport = ASGITransport(app=server.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/tools/explode/invoke", json={"arguments": {}})

        assert response.status_code == 500
        assert "handler exploded" in response.json()["detail"]
