from __future__ import annotations

import pytest

from app.tools.registry import ToolRegistry


class FakeTool:
    """
    Simple fake tool used to test ToolRegistry behavior.
    """

    def __init__(self, name: str, result=None) -> None:
        self.name = name
        self.result = result

    def execute(self, arguments: dict):
        return {
            "tool": self.name,
            "arguments": arguments,
            "result": self.result,
        }


class ToolWithoutName:
    """
    Fake invalid tool without a name attribute.
    """

    def execute(self, arguments: dict):
        return arguments


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_register_tool():
    registry = ToolRegistry()

    tool = FakeTool(
        name="search_documents",
    )

    registry.register(tool)

    assert registry.get_tool("search_documents") is tool


def test_register_all_three_tools():
    registry = ToolRegistry()

    document_search_tool = FakeTool(
        name="search_documents",
    )

    workspace_stats_tool = FakeTool(
        name="get_workspace_stats",
    )

    web_search_tool = FakeTool(
        name="web_search",
    )

    registry.register(document_search_tool)

    registry.register(workspace_stats_tool)

    registry.register(web_search_tool)

    assert registry.list_tools() == [
        "search_documents",
        "get_workspace_stats",
        "web_search",
    ]


def test_register_tool_without_name_raises_error():
    registry = ToolRegistry()

    tool = ToolWithoutName()

    with pytest.raises(
        ValueError,
        match="Cannot register tool without a 'name' attribute.",
    ):
        registry.register(tool)


def test_register_duplicate_tool_raises_error():
    registry = ToolRegistry()

    first_tool = FakeTool(
        name="search_documents",
    )

    second_tool = FakeTool(
        name="search_documents",
    )

    registry.register(first_tool)

    with pytest.raises(
        ValueError,
        match="Tool 'search_documents' is already registered.",
    ):
        registry.register(second_tool)


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


def test_get_tool_returns_registered_tool():
    registry = ToolRegistry()

    tool = FakeTool(
        name="web_search",
    )

    registry.register(tool)

    returned_tool = registry.get_tool(
        "web_search"
    )

    assert returned_tool is tool


def test_get_unknown_tool_raises_error():
    registry = ToolRegistry()

    with pytest.raises(
        ValueError,
        match="Tool 'unknown_tool' is not registered.",
    ):
        registry.get_tool(
            "unknown_tool"
        )


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def test_list_tools_returns_registered_tool_names():
    registry = ToolRegistry()

    registry.register(
        FakeTool(
            name="search_documents",
        )
    )

    registry.register(
        FakeTool(
            name="get_workspace_stats",
        )
    )

    registry.register(
        FakeTool(
            name="web_search",
        )
    )

    tool_names = registry.list_tools()

    assert tool_names == [
        "search_documents",
        "get_workspace_stats",
        "web_search",
    ]


def test_get_all_tools_returns_registered_tools():
    registry = ToolRegistry()

    document_search_tool = FakeTool(
        name="search_documents",
    )

    workspace_stats_tool = FakeTool(
        name="get_workspace_stats",
    )

    registry.register(
        document_search_tool
    )

    registry.register(
        workspace_stats_tool
    )

    tools = registry.get_all_tools()

    assert tools == {
        "search_documents": document_search_tool,
        "get_workspace_stats": workspace_stats_tool,
    }


def test_get_all_tools_returns_copy():
    registry = ToolRegistry()

    tool = FakeTool(
        name="search_documents",
    )

    registry.register(tool)

    tools = registry.get_all_tools()

    tools.clear()

    assert registry.list_tools() == [
        "search_documents",
    ]


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def test_execute_resolves_and_executes_tool():
    registry = ToolRegistry()

    tool = FakeTool(
        name="search_documents",
        result="success",
    )

    registry.register(tool)

    arguments = {
        "query": "How does JWT authentication work?",
        "top_k": 5,
    }

    result = registry.execute(
        name="search_documents",
        arguments=arguments,
    )

    assert result == {
        "tool": "search_documents",
        "arguments": arguments,
        "result": "success",
    }


def test_execute_unknown_tool_raises_error():
    registry = ToolRegistry()

    with pytest.raises(
        ValueError,
        match="Tool 'unknown_tool' is not registered.",
    ):
        registry.execute(
            name="unknown_tool",
            arguments={},
        )