"""Legacy single-node Gemini tool-calling graph implementation.

The active graph separates provider-neutral model work into ``agent.py`` and
tool execution into ``tools.py``. This older factory remains for compatibility
with earlier experiments and uses the native-only registry.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.graph.state import ChatState
from app.services.tool_calling_service import (
    ToolCallingService,
)
from app.tools.tool_registry_factory import (
    create_tool_registry,
)


def create_tool_calling_node(
    db: Session,
):
    """Return the older node that delegates directly to ToolCallingService."""

    def tool_calling_node(
        state: ChatState,
    ) -> dict:
        """Build native tools for one user and request a legacy Gemini response."""

        query = state["query"]

        # -----------------------------------------------------
        # user_id enters LangGraph as a string.
        #
        # Convert it back to UUID because repositories and the
        # ToolRegistry factory use the application's UUID type.
        # -----------------------------------------------------

        user_id = UUID(
            state["user_id"]
        )

        # -----------------------------------------------------
        # Create user-scoped registry.
        #
        # The authenticated user identity comes from ChatService
        # and is never supplied by the LLM.
        # -----------------------------------------------------

        tool_registry = create_tool_registry(
            db=db,
            user_id=user_id,
        )

        # -----------------------------------------------------
        # Create ToolCallingService.
        # -----------------------------------------------------

        tool_calling_service = ToolCallingService(
            tool_registry=tool_registry,
        )

        # -----------------------------------------------------
        # Execute the complete Gemini tool-calling loop.
        # -----------------------------------------------------

        response = (
            tool_calling_service.generate_response(
                query=query,
            )
        )

        # -----------------------------------------------------
        # Final graph result.
        # -----------------------------------------------------

        return {
            "response": response,
            "sources": [],
        }

    return tool_calling_node
