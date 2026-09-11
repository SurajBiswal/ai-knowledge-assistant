from __future__ import annotations

from typing import Any, TypedDict

from app.rag.retriever import RetrievedChunk


class ToolCall(TypedDict):
    """
    Structured tool call requested by Gemini.

    The LLM decides:

    - which tool to call
    - what arguments to provide

    The application decides:

    - whether the tool exists
    - how it is executed
    - authenticated user context
    """

    name: str
    arguments: dict[str, Any]


class ToolResult(TypedDict):
    """
    Structured result produced by the application's Tool Node.
    """

    name: str
    result: dict[str, Any]


class ChatState(TypedDict, total=False):
    """
    Shared state passed between LangGraph nodes.

    Part 7 architecture:

        START
          ↓
        Agent
          ↓
        Tool needed?
          │
          ├── No
          │     ↓
          │    END
          │
          └── Yes
                ↓
             Tool Node
                ↓
             Agent
                ↓
               END
    """

    # ---------------------------------------------------------
    # Authenticated conversation information
    # ---------------------------------------------------------

    user_id: str

    conversation_id: str

    query: str

    messages: list[dict[str, Any]]

    # ---------------------------------------------------------
    # Tool calling state
    # ---------------------------------------------------------

    tool_calls: list[ToolCall]

    tool_results: list[ToolResult]

    gemini_contents: list[Any]

    # ---------------------------------------------------------
    # Final assistant response
    # ---------------------------------------------------------

    response: str

    # ---------------------------------------------------------
    # Legacy RAG state
    #
    # Retained for compatibility with existing components.
    # ---------------------------------------------------------

    retrieved_docs: list[RetrievedChunk]

    sources: list[dict[str, Any]]

    context: str

    prompt: str