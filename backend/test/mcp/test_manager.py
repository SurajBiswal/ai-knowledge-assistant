from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.mcp.client import manager as manager_module
from app.mcp.client.manager import MCPClientManager
from app.mcp.config.server_config import MCPServerConfig


class FakeClient:
    """Simulates the SDK client without opening a real connection."""

    def __init__(self, target):
        self.target = target
        self.call_tool = AsyncMock(
            return_value=SimpleNamespace(
                is_error=False,
                content=[],
            )
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def list_tools(self, cursor=None, cache_mode="use"):
        return SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name="search_documents",
                    description="Search available documents",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        },
                    },
                )
            ],
            next_cursor=None,
        )


@pytest.mark.asyncio
async def test_manager_lifecycle(monkeypatch):
    monkeypatch.setattr(manager_module, "Client", FakeClient)

    config = MCPServerConfig(
        name="test-server",
        transport="stdio",
        command="python",
        args=("-m", "fake_server"),
    )

    manager = MCPClientManager([config])

    # Initially disconnected.
    assert manager.list_servers()[0]["status"] == "disconnected"

    # Connect and discover.
    connected = await manager.connect("test-server")
    assert connected["status"] == "connected"
    assert connected["tool_count"] == 1

    tools = await manager.discover_tools("test-server")
    assert tools[0]["name"] == "search_documents"

    # Invoke the discovered tool.
    result = await manager.call_tool(
        "test-server",
        "search_documents",
        {"query": "MCP architecture"},
    )
    assert result.is_error is False

    # Check health.
    health = await manager.health_check("test-server")
    assert health[0]["healthy"] is True

    # Disconnect and confirm state.
    disconnected = await manager.disconnect("test-server")
    assert disconnected["status"] == "disconnected"
    assert manager.list_servers()[0]["status"] == "disconnected"