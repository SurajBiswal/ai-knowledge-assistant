from __future__ import annotations

from typing import Any, TypedDict

from app.llm.base import ToolCallingConversation, ToolCallingLLM
from app.rag.retriever import RetrievedChunk


class ToolCall(TypedDict):
    """
    Structured tool call requested by the selected LLM.

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
    call_id: str | None


class ToolResult(TypedDict):
    """
    Structured result produced by the application's Tool Node.
    """

    name: str
    result: dict[str, Any]
    call_id: str | None


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

    # The selected client and its normalized conversation are retained for
    # the Tool Node -> Agent return path. This keeps the same model active
    # throughout one tool-calling exchange.
    llm_client: ToolCallingLLM

    llm_conversation: ToolCallingConversation

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
