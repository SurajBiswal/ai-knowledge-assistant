"""Provider-neutral LangGraph node that communicates with the selected LLM.

It builds the current user's unified tool registry, converts tools into shared
definitions, asks the LLM for text or tool calls, and keeps the same client and
conversation alive when the Tool Node returns results.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.graph.state import ChatState
from app.llm.base import (
    ToolCallingConversation,
    ToolCallingLLM,
    ToolDefinition,
    ToolResult,
)
from app.llm.factory import LLMProviderFactory
from app.tools.registry import ToolRegistry
from app.tools.tool_registry_factory import (
    create_unified_tool_registry,
    resolve_tool_registry,
)

# This factory creates the agent node. The node loads every tool available to
# the current user, asks the selected LLM what to do, and keeps turn state.
def create_agent_node(
    db: Session,
    *,
    tool_registry_factory: Callable[..., Any] = create_unified_tool_registry,
    llm_provider_factory: Callable[..., LLMProviderFactory] = LLMProviderFactory,
):
    """Return an async Agent Node configured with registry and LLM factories."""

    # The agent node is async because MCP providers discover remote tools before
    # those tool definitions can be sent to the LLM.
    async def agent_node(state: ChatState) -> dict[str, Any]:
        """Process one model turn and return tool calls or a final response."""
        user_id = UUID(state["user_id"])
        tool_registry = state.get("tool_registry")
        if tool_registry is None:
            tool_registry = await resolve_tool_registry(
                tool_registry_factory,
                db=db,
                user_id=user_id,
            )
        tool_definitions = _build_tool_definitions(tool_registry)

        if state.get("tool_results"):
            llm, conversation = _get_existing_turn_state(state)
            llm.add_tool_results(
                conversation,
                [
                    ToolResult(
                        name=result["name"],
                        result=result["result"],
                        call_id=result.get("call_id"),
                    )
                    for result in state["tool_results"]
                ],
            )
        else:
            llm = llm_provider_factory(db=db).create_for_user(user_id=user_id)
            conversation = llm.start_conversation(state["query"])

        model_response = llm.generate(conversation, tool_definitions)
        tool_calls = [
            {
                "name": tool_call.name,
                "arguments": dict(tool_call.arguments),
                "call_id": tool_call.call_id,
            }
            for tool_call in model_response.tool_calls
        ]

        if tool_calls:
            return {
                "tool_calls": tool_calls,
                "tool_results": [],
                "llm_client": llm,
                "llm_conversation": conversation,
                "tool_registry": tool_registry,
                "response": "",
            }

        if not model_response.text:
            raise RuntimeError(
                "Selected LLM returned neither text nor tool calls."
            )

        _close_client(llm)
        return {
            "tool_calls": [],
            "response": model_response.text,
        }

    return agent_node


# This helper translates every registered tool into the provider-neutral schema
# expected by all supported LLM clients.
def _build_tool_definitions(
    tool_registry: ToolRegistry,
) -> list[ToolDefinition]:
    definitions = []

    for tool in tool_registry.get_all_tools().values():
        definition = tool.get_definition()
        definitions.append(
            ToolDefinition(
                name=definition["name"],
                description=definition["description"],
                parameters=definition["input_schema"],
            )
        )

    return definitions


# This helper retrieves the exact LLM client and conversation used before tools
# ran, preventing a provider switch in the middle of one agent turn.
def _get_existing_turn_state(
    state: ChatState,
) -> tuple[ToolCallingLLM, ToolCallingConversation]:
    llm = state.get("llm_client")
    conversation = state.get("llm_conversation")

    if llm is None or conversation is None:
        raise RuntimeError(
            "Missing LLM conversation state after tool execution."
        )

    return llm, conversation


# This helper releases provider clients that expose a close method.
def _close_client(llm: ToolCallingLLM) -> None:
    close = getattr(llm, "close", None)
    if callable(close):
        close()
