"""Typed structure shared between LangGraph nodes.

ChatService creates the initial values. Agent and Tool Nodes add model clients,
tool calls, tool results, and the final response as the graph runs. TypedDict
documents expected keys without creating runtime objects or database records.
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.llm.base import ToolCallingConversation, ToolCallingLLM
from app.rag.retriever import RetrievedChunk
from app.tools.registry import ToolRegistry


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

    name: str  # Public registry name selected by the model.
    arguments: dict[str, Any]  # Model-supplied input validated by the tool.
    call_id: str | None  # Provider ID used to match the later result.


class ToolResult(TypedDict):
    """
    Structured result produced by the application's Tool Node.
    """

    name: str  # Tool that produced the result.
    result: dict[str, Any]  # JSON-safe output returned to the model.
    call_id: str | None  # Same ID as the matching ToolCall.


class ChatState(TypedDict, total=False):
    """
    Shared state passed between LangGraph nodes.

    Active architecture:

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

    user_id: str  # Authenticated owner, serialized as text for graph state.

    conversation_id: str  # Conversation receiving the current message.

    query: str  # Current user question passed to the selected LLM.

    messages: list[dict[str, Any]]  # Recent stored history from ChatService.

    # ---------------------------------------------------------
    # Tool calling state
    # ---------------------------------------------------------

    tool_calls: list[ToolCall]  # Work requested by the latest model response.

    tool_results: list[ToolResult]  # Completed work returned by the Tool Node.

    # The selected client and its normalized conversation are retained for
    # the Tool Node -> Agent return path. This keeps the same model active
    # throughout one tool-calling exchange.
    llm_client: ToolCallingLLM

    llm_conversation: ToolCallingConversation

    # The same user-scoped registry is shared by the agent and Tool Node so an
    # MCP server is discovered once and the advertised tool is the executed one.
    tool_registry: ToolRegistry

    # ---------------------------------------------------------
    # Final assistant response
    # ---------------------------------------------------------

    response: str  # Final natural-language answer returned to ChatService.

    # ---------------------------------------------------------
    # Legacy RAG state
    #
    # Retained for compatibility with existing components.
    # ---------------------------------------------------------

    retrieved_docs: list[RetrievedChunk]

    sources: list[dict[str, Any]]

    context: str

    prompt: str
