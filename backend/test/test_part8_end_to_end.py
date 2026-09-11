from __future__ import annotations

from uuid import UUID

from app.database.session import SessionLocal
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.chat_service import ChatService


# Real conversation ID belonging to the user.
CONVERSATION_ID = UUID("580fc6c3-b356-408f-bdbd-696d9edb0c27")


def run_test(
    chat_service: ChatService,
    label: str,
    question: str,
) -> None:
    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)
    print(f"USER: {question}")

    try:
        result = chat_service.send_message(
            conversation_id=CONVERSATION_ID,
            user_message=question,
        )

        print("\nASSISTANT:")
        print(result)

    except Exception as exc:
        print("\n❌ TEST FAILED")
        print(f"{type(exc).__name__}: {exc}")


def main() -> None:
    db = SessionLocal()

    try:
        # ---------------------------------------------------------
        # CREATE CHAT SERVICE
        # ---------------------------------------------------------
        conversation_repository = ConversationRepository(db)
        message_repository = MessageRepository(db)

        chat_service = ChatService(
            conversation_repository=conversation_repository,
            message_repository=message_repository,
        )

        # ---------------------------------------------------------
        # TEST 1 — NO TOOL
        # ---------------------------------------------------------
        run_test(
            chat_service,
            "TEST 1 — Direct LLM Answer",
            "Hello, how are you?",
        )

        # ---------------------------------------------------------
        # TEST 2 — WORKSPACE STATS TOOL
        # ---------------------------------------------------------
        run_test(
            chat_service,
            "TEST 2 — Workspace Stats Tool",
            "How many documents do I have in my workspace?",
        )

        # ---------------------------------------------------------
        # TEST 3 — DOCUMENT SEARCH TOOL
        # ---------------------------------------------------------
        run_test(
            chat_service,
            "TEST 3 — Document Search Tool",
            "When Arin understood that the future wasn't something he was supposed to remember?",
        )

        # ---------------------------------------------------------
        # TEST 4 — WEB SEARCH TOOL
        # ---------------------------------------------------------
        run_test(
            chat_service,
            "TEST 4 — Web Search Tool",
            "Search the web and tell me what the latest major developments in artificial intelligence are.",
        )

        # ---------------------------------------------------------
        # TEST 5 — NO TOOL / GENERAL KNOWLEDGE
        # ---------------------------------------------------------
        run_test(
            chat_service,
            "TEST 5 — General Knowledge",
            "What is 25 multiplied by 4?",
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()