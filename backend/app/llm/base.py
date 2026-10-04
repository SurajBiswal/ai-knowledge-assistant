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

KNOWLEDGE_AI_SYSTEM_PROMPT = """You are KnowledgeAI, an assistant for a user's personal knowledge base. Answer questions from the user's uploaded documents when relevant by using the search_documents tool. If a question is about your identity or capabilities, answer from this context rather than general knowledge. Be clear about when the available documents do not contain the answer."""


class LLMProviderError(RuntimeError):
    """Raised when a configured LLM cannot complete a valid request."""


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """A provider-neutral function declaration exposed to a model."""

    name: str
    description: str
    parameters: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A function call requested by an LLM."""

    name: str
    arguments: Mapping[str, Any]
    call_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolResult:
    """A structured result returned by an application tool."""

    name: str
    result: Mapping[str, Any]
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

    text: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(slots=True)
class ConversationMessage:
    """A normalized conversation item retained between model turns."""

    role: Literal["system", "user", "assistant", "tool"]
    text: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()


@dataclass(slots=True)
class ToolCallingConversation:
    """Mutable, provider-neutral history for one tool-calling exchange."""

    messages: list[ConversationMessage] = field(default_factory=list)


class ToolCallingLLM(ABC):
    """Contract consumed by the future dynamic client factory and agent.

    Implementations translate the normalized conversation into their native
    request format and translate their response back into ``ModelResponse``.
    The agent therefore never needs to know a provider's SDK classes.
    """

    def start_conversation(self, query: str) -> ToolCallingConversation:
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
        if not tool_results:
            raise ValueError("Tool results cannot be empty.")

        conversation.messages.append(
            ConversationMessage(
                role="tool",
                tool_results=tuple(tool_results),
            )
        )
