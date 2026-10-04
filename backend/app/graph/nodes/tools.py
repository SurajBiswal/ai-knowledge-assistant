from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.graph.state import ChatState
from app.llm.base import serialize_tool_output
from app.tools.tool_registry_factory import (
    create_tool_registry,
)


def create_tool_node(
    db: Session,
    *,
    tool_registry_factory=create_tool_registry,
):
    """
    Create the LangGraph Tool Node.

    Responsibilities:

        1. Read tool calls from graph state
        2. Create authenticated user's ToolRegistry
        3. Execute requested tools
        4. Serialize structured results
        5. Return results to graph state

    The Tool Node does NOT decide which tool to use.

    The selected LLM made that decision.
    """

    def tool_node(
        state: ChatState,
    ) -> dict[str, Any]:

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

        tool_registry = tool_registry_factory(
            db=db,
            user_id=user_id,
        )

        tool_results = []

        # -----------------------------------------------------
        # Execute every LLM-requested tool
        # -----------------------------------------------------

        for tool_call in tool_calls:

            tool_name = tool_call["name"]

            arguments = tool_call[
                "arguments"
            ]

            raw_result = (
                tool_registry.execute(
                    name=tool_name,
                    arguments=arguments,
                )
            )

            serialized_result = serialize_tool_output(raw_result)

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
        }

    return tool_node
