from uuid import UUID

from app.core.dependencies import get_db
from app.services.tool_calling_service import (
    ToolCallingService,
)
from app.tools.tool_registry_factory import (
    create_tool_registry,
)


def run_test(
    user_id: str,
    query: str,
) -> None:
    """
    Run one real end-to-end Layer 1 tool-calling test.

    Flow:

        User query
            ↓
        Gemini + tool schemas
            ↓
        Tool decision
            ↓
        ToolRegistry
            ↓
        Tool execution
            ↓
        Gemini final answer
    """

    db = next(get_db())

    try:

        registry = create_tool_registry(
            db=db,
            user_id=UUID(user_id),
        )

        service = ToolCallingService(
            tool_registry=registry,
        )

        response = service.generate_response(
            query=query,
        )

        print("\n=== FINAL RESPONSE ===\n")

        print(response)

    finally:

        db.close()


if __name__ == "__main__":

    USER_ID = (
        "82ff9f42-6ee7-4379-9227-f12f9805adc9"
    )

    # QUERY = (
    #     "How many documents have I uploaded "
    #     "to my workspace?"
    # )

    # QUERY = (
    #     "What message did the mysterious device reveal?"
    # )

    # QUERY = (
    #     "What are the latest major AI developments?"
    # )

    QUERY = "Hi, how are you?"

    run_test(
        user_id=USER_ID,
        query=QUERY,
    )