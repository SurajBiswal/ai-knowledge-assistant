import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.graph.nodes.agent import _build_tool_definitions
from app.mcp.adapters.tool_adapter import (
    MAX_OUTPUT_CHARS,
    MCPToolAdapter,
)
from app.tools.registry import ToolRegistry


class TextContent:
    def __init__(self, text: str) -> None:
        self.text = text


class ImageContent:
    pass


class AudioContent:
    pass


class ResourceContent:
    pass


def make_adapter(manager) -> MCPToolAdapter:
    return MCPToolAdapter(
        manager=manager,
        server_name="GitHub Server",
        remote_tool_name="search/repositories",
        description="Search GitHub repositories.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )


def test_definition_preserves_mcp_json_schema_and_namespaces_tool():
    adapter = make_adapter(AsyncMock())

    definition = adapter.get_definition()

    assert definition == {
        "name": "mcp_github_server_search_repositories",
        "description": "Search GitHub repositories.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    }


def test_agent_builds_definition_from_mcp_schema():
    registry = ToolRegistry()
    registry.register(make_adapter(AsyncMock()))

    definitions = _build_tool_definitions(registry)

    assert len(definitions) == 1
    assert definitions[0].name == "mcp_github_server_search_repositories"
    assert definitions[0].parameters == {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }


def test_execute_async_calls_manager_and_normalizes_content():
    manager = SimpleNamespace(
        call_tool=AsyncMock(
            return_value=SimpleNamespace(
                is_error=False,
                structured_content={"count": 1},
                content=[
                    TextContent("one result"),
                    ImageContent(),
                    AudioContent(),
                    ResourceContent(),
                ],
            )
        )
    )
    adapter = make_adapter(manager)

    result = asyncio.run(
        adapter.execute_async({"query": "langgraph"})
    )

    manager.call_tool.assert_awaited_once_with(
        server_name="GitHub Server",
        tool_name="search/repositories",
        arguments={"query": "langgraph"},
    )
    assert result["is_error"] is False
    assert result["structured_content"] == {"count": 1}
    assert result["content"] == [
        {"type": "text", "text": "one result"},
        {
            "type": "image",
            "omitted": True,
            "reason": "Binary image content is not forwarded.",
        },
        {
            "type": "audio",
            "omitted": True,
            "reason": "Binary audio content is not forwarded.",
        },
        {
            "type": "unsupported",
            "content_type": "ResourceContent",
            "omitted": True,
        },
    ]


def test_execute_async_rejects_non_dictionary_arguments():
    adapter = make_adapter(AsyncMock())

    with pytest.raises(TypeError, match="must be a dictionary"):
        asyncio.run(adapter.execute_async(["invalid"]))


def test_execute_async_omits_oversized_output():
    manager = SimpleNamespace(
        call_tool=AsyncMock(
            return_value=SimpleNamespace(
                is_error=False,
                structured_content={"payload": "x" * (MAX_OUTPUT_CHARS + 1)},
                content=[],
            )
        )
    )
    adapter = make_adapter(manager)

    result = asyncio.run(adapter.execute_async({}))

    assert result["truncated"] is True
    assert result["structured_content"] is None
    assert result["content"][0]["text"].startswith("MCP output omitted")


def test_synchronous_execution_is_rejected_explicitly():
    adapter = make_adapter(AsyncMock())

    with pytest.raises(RuntimeError, match="execute_async"):
        adapter.execute({})
