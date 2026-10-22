"""Provider-neutral contract for an LLM that can call application tools.

The Week 9 graph needs two model interactions: one to decide whether a tool
is needed, then one or more follow-up interactions after tool results are
available.  This module represents that loop without exposing Gemini or
OpenAI-compatible SDK objects to the agent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

# Every provider receives the same identity and document-search instructions.
KNOWLEDGE_AI_SYSTEM_PROMPT = """You are KnowledgeAI, an assistant for a user's personal knowledge base. Answer questions from the user's uploaded documents when relevant by using the search_documents tool. If a question is about your identity or capabilities, answer from this context rather than general knowledge. Be clear about when the available documents do not contain the answer."""


class LLMProviderError(RuntimeError):
    """Raised when a configured LLM cannot complete a valid request."""


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """A provider-neutral function declaration exposed to a model."""

    # Public registry name the model must return when requesting this tool.
    name: str
    # Plain-language purpose used by the model when choosing a tool.
    description: str
    # JSON Schema describing arguments the model is allowed to provide.
    parameters: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A function call requested by an LLM."""

    # Tool name and model-generated arguments consumed by the Tool Node.
    name: str
    arguments: Mapping[str, Any]
    # Provider call ID links the result to the original request when available.
    call_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolResult:
    """A structured result returned by an application tool."""

    # Name/result are returned to the model after application execution.
    name: str
    result: Mapping[str, Any]
    # The same ID from ToolCall preserves provider message ordering.
    call_id: str | None = None


def serialize_tool_output(result: Any) -> dict[str, Any]:
    """Convert a tool output into the JSON-compatible contract payload."""
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")

    if isinstance(result, dict):
        return result

    raise TypeError(
        "Tool result must be a Pydantic model or dictionary."
    )


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """The text and/or tool calls produced by a model turn."""

    # A turn may contain final text, tool requests, or both.
    text: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(slots=True)
class ConversationMessage:
    """A normalized conversation item retained between model turns."""

    # Normalized role and payload used by both Gemini and OpenAI adapters.
    role: Literal["system", "user", "assistant", "tool"]
    text: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()


@dataclass(slots=True)
class ToolCallingConversation:
    """Mutable, provider-neutral history for one tool-calling exchange."""

    # Mutable history kept across agent -> tool -> agent steps for one turn.
    messages: list[ConversationMessage] = field(default_factory=list)


class ToolCallingLLM(ABC):
    """Contract consumed by the dynamic client factory and agent.

    Implementations translate the normalized conversation into their native
    request format and translate their response back into ``ModelResponse``.
    The agent therefore never needs to know a provider's SDK classes.
    """

    def start_conversation(self, query: str) -> ToolCallingConversation:
        """Validate a user query and start history with system and user messages."""
        query = query.strip()
        if not query:
            raise ValueError("Query cannot be empty.")

        return ToolCallingConversation(
            messages=[
                ConversationMessage(
                    role="system",
                    text=KNOWLEDGE_AI_SYSTEM_PROMPT,
                ),
                ConversationMessage(role="user", text=query),
            ]
        )

    @abstractmethod
    def generate(
        self,
        conversation: ToolCallingConversation,
        tools: Sequence[ToolDefinition],
    ) -> ModelResponse:
        """Generate the next model turn and append it to ``conversation``."""

    def add_tool_results(
        self,
        conversation: ToolCallingConversation,
        tool_results: Sequence[ToolResult],
    ) -> None:
        """Append application tool results before the model's follow-up turn."""
        if not tool_results:
            raise ValueError("Tool results cannot be empty.")

        conversation.messages.append(
            ConversationMessage(
                role="tool",
                tool_results=tuple(tool_results),
            )
        )
