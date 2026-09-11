from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.graph.state import ChatState
from app.services.tool_calling_service import (
    ToolCallingService,
)
from app.tools.tool_registry_factory import (
    create_tool_registry,
)


def create_tool_node(
    db: Session,
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

    Gemini made that decision.
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

        tool_registry = create_tool_registry(
            db=db,
            user_id=user_id,
        )

        tool_results = []

        # -----------------------------------------------------
        # Execute every Gemini-requested tool
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

            serialized_result = (
                ToolCallingService
                .serialize_tool_result(
                    raw_result
                )
            )

            tool_results.append(
                {
                    "name": tool_name,
                    "result": serialized_result,
                }
            )

        return {
            "tool_calls": [],
            "tool_results": tool_results,
        }

    return tool_node