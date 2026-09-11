from unittest.mock import Mock

from app.services.web_search_service import WebSearchService
from app.tools.web_search import WebSearchTool


def build_tool():
    search_service = Mock(spec=WebSearchService)

    search_service.search.return_value = [
        {
            "title": "React Official Website",
            "url": "https://react.dev/",
            "snippet": "The library for web and native user interfaces.",
            "source": "react.dev",
        },
        {
            "title": "React Blog",
            "url": "https://react.dev/blog",
            "snippet": "Latest news and updates from the React team.",
            "source": "react.dev",
        },
    ]

    tool = WebSearchTool(
        search_service=search_service,
    )

    return tool, search_service


def test_web_search_tool_calls_search_service():
    tool, search_service = build_tool()

    result = tool.execute(
        {
            "query": "latest React developments",
            "max_results": 5,
        }
    )

    search_service.search.assert_called_once_with(
        query="latest React developments",
        max_results=5,
    )

    assert len(result.results) == 2

    assert result.results[0].title == "React Official Website"
    assert result.results[0].url == "https://react.dev/"
    assert result.results[0].snippet == (
        "The library for web and native user interfaces."
    )
    assert result.results[0].source == "react.dev"


def test_web_search_tool_validates_input():
    tool, search_service = build_tool()

    # Empty query must be rejected by the input schema.
    try:
        tool.execute(
            {
                "query": "",
                "max_results": 5,
            }
        )
    except Exception:
        pass
    else:
        raise AssertionError("Empty query should be rejected.")

    search_service.search.assert_not_called()


def test_web_search_tool_rejects_invalid_max_results():
    tool, search_service = build_tool()

    try:
        tool.execute(
            {
                "query": "React",
                "max_results": 0,
            }
        )
    except Exception:
        pass
    else:
        raise AssertionError(
            "max_results=0 should be rejected."
        )

    search_service.search.assert_not_called()


def test_web_search_tool_rejects_unknown_arguments():
    tool, search_service = build_tool()

    try:
        tool.execute(
            {
                "query": "React",
                "max_results": 5,
                "user_id": "some-user",
            }
        )
    except Exception:
        pass
    else:
        raise AssertionError(
            "Unexpected arguments should be rejected."
        )

    search_service.search.assert_not_called()


def test_web_search_tool_returns_empty_results():
    search_service = Mock(spec=WebSearchService)
    search_service.search.return_value = []

    tool = WebSearchTool(
        search_service=search_service,
    )

    result = tool.execute(
        {
            "query": "some query with no results",
            "max_results": 5,
        }
    )

    assert result.results == []

    search_service.search.assert_called_once_with(
        query="some query with no results",
        max_results=5,
    )