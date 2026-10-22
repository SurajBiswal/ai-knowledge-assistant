from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.tools.providers.access import (
    StaticToolAvailabilityResolver,
    UserToolAvailability,
)
from app.tools.providers.mcp import MCPToolProvider
from app.tools.providers.native import NativeToolProvider
from app.tools.providers.unified import UnifiedToolRegistryFactory
from app.tools.registry import ToolNameCollisionError


# This block uses the same class name as MCP text content so the adapter follows
# its normal safe text-normalization path during the execution test.
class TextContent:
    # This initializer stores the text returned by the fake MCP server.
    def __init__(self, text: str) -> None:
        self.text = text


# This small native tool makes user filtering visible without loading RAG models
# or calling databases in a unit test.
class FakeNativeTool:
    # This initializer gives each fake tool a public registry name.
    def __init__(self, name: str) -> None:
        self.name = name

    # This definition is the metadata that would be sent to the selected LLM.
    def get_definition(self):
        return {
            "name": self.name,
            "description": f"Native test tool {self.name}",
            "input_schema": {"type": "object"},
        }

    # This method represents the unchanged synchronous native execution path.
    def execute(self, arguments: dict):
        return {"tool": self.name, "arguments": arguments}


# This manager simulates several MCP servers, live discovery, and async calls
# while recording which servers and tools the application actually touched.
class FakeMCPManager:
    # This initializer accepts tool metadata grouped by MCP server name.
    def __init__(self, tools_by_server: dict[str, list[dict]]) -> None:
        self.tools_by_server = tools_by_server
        self.statuses = {
            server_name: "disconnected"
            for server_name in tools_by_server
        }
        self.connect_calls: list[str] = []
        self.discovery_calls: list[str] = []
        self.tool_calls: list[dict] = []

    # This method exposes all configured servers to the MCP provider.
    def list_servers(self):
        return [
            {
                "name": server_name,
                "transport": "stdio",
                "status": status,
                "tool_count": len(self.tools_by_server[server_name]),
            }
            for server_name, status in self.statuses.items()
        ]

    # This async method records connection work and marks a server as ready.
    async def connect(self, server_name: str):
        self.connect_calls.append(server_name)
        self.statuses[server_name] = "connected"
        return {"server": server_name, "status": "connected"}

    # This async method returns the server's current metadata on every request,
    # which lets the tests prove discovery is dynamic instead of hardcoded.
    async def discover_tools(self, server_name: str):
        self.discovery_calls.append(server_name)
        return list(self.tools_by_server[server_name])

    # This async method behaves like a remote tool invocation for adapter tests.
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict,
    ):
        self.tool_calls.append(
            {
                "server": server_name,
                "tool": tool_name,
                "arguments": arguments,
            }
        )
        return SimpleNamespace(
            is_error=False,
            structured_content={"ok": True},
            content=[TextContent("remote result")],
        )


# This helper creates one piece of MCP discovery metadata in the shape returned
# by MCPClientManager.discover_tools().
def discovered_tool(name: str) -> dict:
    return {
        "name": name,
        "description": f"Remote test tool {name}",
        "input_schema": {
            "type": "object",
            "properties": {"value": {"type": "string"}},
        },
    }


# This test proves native and remote tools from multiple servers share one
# registry while two users receive different, explicitly allowed capabilities.
@pytest.mark.asyncio
async def test_unified_registry_applies_per_user_availability() -> None:
    user_a = uuid4()
    user_b = uuid4()
    manager = FakeMCPManager(
        {
            "github": [
                discovered_tool("search_repositories"),
                discovered_tool("list_issues"),
            ],
            "filesystem": [discovered_tool("read_file")],
        }
    )
    resolver = StaticToolAvailabilityResolver(
        availability_by_user={
            user_a: UserToolAvailability(
                native_tool_names=frozenset({"search_documents"}),
                mcp_server_names=frozenset({"github", "filesystem"}),
                mcp_tool_names={
                    "github": frozenset({"search_repositories"}),
                    "filesystem": frozenset({"read_file"}),
                },
            ),
            user_b: UserToolAvailability(
                native_tool_names=frozenset({"web_search"}),
                mcp_server_names=frozenset({"github"}),
                mcp_tool_names={
                    "github": frozenset({"list_issues"}),
                },
            ),
        }
    )
    native_provider = NativeToolProvider(
        db=Mock(),
        availability_resolver=resolver,
        tool_builder=lambda _db, _user_id: [
            FakeNativeTool("search_documents"),
            FakeNativeTool("web_search"),
        ],
    )
    mcp_provider = MCPToolProvider(manager, resolver)
    factory = UnifiedToolRegistryFactory([native_provider, mcp_provider])

    registry_a = await factory.create(user_a)
    registry_b = await factory.create(user_b)

    assert registry_a.list_tools() == [
        "search_documents",
        "mcp_github_search_repositories",
        "mcp_filesystem_read_file",
    ]
    assert registry_b.list_tools() == [
        "web_search",
        "mcp_github_list_issues",
    ]
    assert manager.connect_calls == ["github", "filesystem"]
    assert manager.discovery_calls == [
        "github",
        "filesystem",
        "github",
    ]

    remote_result = await registry_a.execute_async(
        "mcp_filesystem_read_file",
        {"value": "README.md"},
    )
    assert remote_result["structured_content"] == {"ok": True}
    assert manager.tool_calls[-1] == {
        "server": "filesystem",
        "tool": "read_file",
        "arguments": {"value": "README.md"},
    }


# This test proves each registry creation refreshes MCP discovery, allowing a
# server to add a tool without changing application code or restarting it.
@pytest.mark.asyncio
async def test_mcp_provider_discovers_new_tools_dynamically() -> None:
    user_id = uuid4()
    manager = FakeMCPManager(
        {"github": [discovered_tool("search_repositories")]}
    )
    resolver = StaticToolAvailabilityResolver(
        availability_by_user={
            user_id: UserToolAvailability(
                mcp_server_names=frozenset({"github"}),
            )
        }
    )
    factory = UnifiedToolRegistryFactory(
        [MCPToolProvider(manager, resolver)]
    )

    first_registry = await factory.create(user_id)
    manager.tools_by_server["github"].append(discovered_tool("list_issues"))
    second_registry = await factory.create(user_id)

    assert first_registry.list_tools() == [
        "mcp_github_search_repositories"
    ]
    assert second_registry.list_tools() == [
        "mcp_github_search_repositories",
        "mcp_github_list_issues",
    ]


# This test proves users without an explicit MCP grant never connect to or see
# remote servers, even when those servers are configured in the manager.
@pytest.mark.asyncio
async def test_mcp_access_is_denied_by_default() -> None:
    manager = FakeMCPManager(
        {"github": [discovered_tool("search_repositories")]}
    )
    provider = MCPToolProvider(
        manager,
        StaticToolAvailabilityResolver(),
    )

    tools = await provider.get_tools(uuid4())

    assert tools == []
    assert manager.connect_calls == []
    assert manager.discovery_calls == []


# This test proves server-name normalization cannot silently overwrite a tool
# when two different MCP servers produce the same public registry name.
@pytest.mark.asyncio
async def test_unified_registry_rejects_mcp_name_collisions() -> None:
    user_id = uuid4()
    manager = FakeMCPManager(
        {
            "Git Hub": [discovered_tool("echo")],
            "git_hub": [discovered_tool("echo")],
        }
    )
    resolver = StaticToolAvailabilityResolver(
        availability_by_user={
            user_id: UserToolAvailability(
                mcp_server_names=frozenset({"Git Hub", "git_hub"}),
            )
        }
    )
    factory = UnifiedToolRegistryFactory(
        [MCPToolProvider(manager, resolver)]
    )

    with pytest.raises(
        ToolNameCollisionError,
        match="mcp_git_hub_echo.*Git Hub.*git_hub",
    ):
        await factory.create(user_id)
