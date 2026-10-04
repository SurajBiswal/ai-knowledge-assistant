"""Provider-neutral LangGraph agent node for the Week 9 tool loop."""

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
from app.tools.tool_registry_factory import create_tool_registry


def create_agent_node(
    db: Session,
    *,
    tool_registry_factory: Callable[..., ToolRegistry] = create_tool_registry,
    llm_provider_factory: Callable[..., LLMProviderFactory] = LLMProviderFactory,
):
    """Create the agent side of the existing Week 9 tool-calling loop.

    The graph routing and Tool Node are unchanged. This node now only asks
    the Phase 8 factory for the authenticated user's LLM and speaks the
    Phase 7 provider-neutral contract instead of Gemini SDK types.
    """

    def agent_node(state: ChatState) -> dict[str, Any]:
        user_id = UUID(state["user_id"])
        tool_registry = tool_registry_factory(db=db, user_id=user_id)
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


def _build_tool_definitions(
    tool_registry: ToolRegistry,
) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name=tool.name,
            description=tool.description,
            parameters=tool.input_schema.model_json_schema(),
        )
        for tool in tool_registry.get_all_tools().values()
    ]


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


def _close_client(llm: ToolCallingLLM) -> None:
    close = getattr(llm, "close", None)
    if callable(close):
        close()
