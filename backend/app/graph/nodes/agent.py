from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.graph.state import ChatState
from app.services.tool_calling_service import (
    ToolCallingService,
)
from app.tools.tool_registry_factory import (
    create_tool_registry,
)


def create_agent_node(
    db: Session,
):
    """
    Create the LangGraph Agent Node.

    The Agent Node is responsible for:

        - Creating the authenticated user's ToolRegistry
        - Calling Gemini
        - Detecting tool calls
        - Returning either:
            * tool_calls
            * final response

    The Agent Node does NOT execute tools.
    """

    def agent_node(
        state: ChatState,
    ) -> dict[str, Any]:

        # -----------------------------------------------------
        # Create user-scoped registry
        # -----------------------------------------------------

        from uuid import UUID

        user_id = UUID(
            state["user_id"]
        )

        tool_registry = create_tool_registry(
            db=db,
            user_id=user_id,
        )

        tool_service = ToolCallingService(
            tool_registry=tool_registry,
        )

        # -----------------------------------------------------
        # First Agent execution
        # -----------------------------------------------------

        if not state.get("tool_results"):

            contents = (
                tool_service.create_initial_contents(
                    query=state["query"],
                )
            )

        # -----------------------------------------------------
        # Continue after Tool Node
        # -----------------------------------------------------

        else:

            previous_contents = state.get(
                "gemini_contents"
            )

            if not previous_contents:
                raise RuntimeError(
                    "Missing Gemini conversation state "
                    "after tool execution."
                )

            tool_result_content = (
                tool_service.create_tool_result_content(
                    tool_results=state[
                        "tool_results"
                    ],
                )
            )

            contents = (
                previous_contents
                + [tool_result_content]
            )

        # -----------------------------------------------------
        # Ask Gemini what to do
        # -----------------------------------------------------

        response = tool_service.call_model(
            contents=contents,
        )

        tool_calls = (
            tool_service.extract_tool_calls(
                response=response,
            )
        )

        # -----------------------------------------------------
        # Gemini requested tools
        # -----------------------------------------------------

        if tool_calls:

            model_content = (
                tool_service.get_model_content(
                    response=response,
                )
            )

            return {
                "tool_calls": tool_calls,
                "tool_results": [],
                "gemini_contents": (
                    contents
                    + [model_content]
                ),
                "response": "",
            }

        # -----------------------------------------------------
        # Gemini produced final answer
        # -----------------------------------------------------

        final_response = (
            tool_service.extract_final_response(
                response=response,
            )
        )

        return {
            "tool_calls": [],
            "response": final_response,
        }

    return agent_node