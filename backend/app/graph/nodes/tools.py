"""LangGraph node that executes model-requested application tools.

The node receives structured calls from ``agent.py``, looks up each tool in the
same user-scoped registry, awaits MCP tools or runs native tools, and returns
JSON-safe results to the Agent Node for the model's next turn.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.graph.state import ChatState
from app.llm.base import serialize_tool_output
from app.tools.tool_registry_factory import (
    create_unified_tool_registry,
    resolve_tool_registry,
)


MAX_CITATION_EXCERPT_CHARS = 320


# This helper turns document-search results into the citation shape stored on
# assistant messages and rendered by the frontend's Sources component.
def _merge_document_sources(
    existing_sources: list[dict[str, Any]],
    tool_name: str,
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Add unique document citations without trusting arbitrary tool output."""
    sources = [dict(source) for source in existing_sources]
    if tool_name != "search_documents":
        return sources

    seen = {
        (
            source.get("filename"),
            source.get("page"),
        )
        for source in sources
    }
    raw_results = result.get("results", [])
    if not isinstance(raw_results, list):
        return sources

    for item in raw_results:
        if not isinstance(item, dict):
            continue
        filename = item.get("document")
        if not isinstance(filename, str) or not filename.strip():
            continue
        page = item.get("page")
        if isinstance(page, bool) or not isinstance(page, int):
            page = None
        key = (filename.strip(), page)
        if key in seen:
            continue

        content = item.get("content")
        excerpt = None
        if isinstance(content, str) and content.strip():
            excerpt = content.strip()[:MAX_CITATION_EXCERPT_CHARS]

        sources.append(
            {
                "document_id": item.get("document_id"),
                "filename": filename.strip(),
                "page": page,
                "chunk_index": item.get("chunk_index"),
                "excerpt": excerpt,
            }
        )
        seen.add(key)

    return sources


# This factory creates an async graph node so remote MCP calls can be awaited
# while native synchronous tools continue to run through the same registry.
def create_tool_node(
    db: Session,
    *,
    tool_registry_factory=create_unified_tool_registry,
):
    """
    Return an async Tool Node using the supplied registry factory.

    Responsibilities:

        1. Read tool calls from graph state
        2. Create authenticated user's ToolRegistry
        3. Execute requested tools
        4. Serialize structured results
        5. Return results to graph state

    The Tool Node does NOT decide which tool to use.

    The selected LLM made that decision.
    """

    # This node executes every tool requested by the LLM and returns normalized
    # results to the agent for the next turn of the existing tool loop.
    async def tool_node(
        state: ChatState,
    ) -> dict[str, Any]:
        """Execute state tool calls and return results linked by call ID."""

        tool_calls = state.get(
            "tool_calls",
            [],
        )

        if not tool_calls:
            raise RuntimeError(
                "Tool Node was reached without tool calls."
            )

        # -----------------------------------------------------
        # Create authenticated user's registry
        # -----------------------------------------------------

        user_id = UUID(
            state["user_id"]
        )

        tool_registry = state.get("tool_registry")
        if tool_registry is None:
            tool_registry = await resolve_tool_registry(
                tool_registry_factory,
                db=db,
                user_id=user_id,
            )

        tool_results = []
        sources = list(state.get("sources") or [])

        # -----------------------------------------------------
        # Execute every LLM-requested tool
        # -----------------------------------------------------

        for tool_call in tool_calls:

            tool_name = tool_call["name"]

            arguments = tool_call[
                "arguments"
            ]

            raw_result = await tool_registry.execute_async(
                name=tool_name,
                arguments=arguments,
            )

            serialized_result = serialize_tool_output(raw_result)

            sources = _merge_document_sources(
                existing_sources=sources,
                tool_name=tool_name,
                result=serialized_result,
            )

            tool_results.append(
                {
                    "name": tool_name,
                    "result": serialized_result,
                    "call_id": tool_call.get("call_id"),
                }
            )

        return {
            "tool_calls": [],
            "tool_results": tool_results,
            "sources": sources,
        }

    return tool_node
