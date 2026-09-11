from uuid import UUID

from app.core.dependencies import get_db
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.message_repository import MessageRepository
from app.tools.workspace_stats import WorkspaceStatsTool


def main():
    # Use the UUID of a real user from your database.
    user_id = UUID("82ff9f42-6ee7-4379-9227-f12f9805adc9")

    db = next(get_db())

    try:
        document_repository = DocumentRepository(db=db)
        chunk_repository = DocumentChunkRepository(db=db)
        conversation_repository = ConversationRepository(db=db)
        message_repository = MessageRepository(db=db)

        tool = WorkspaceStatsTool(
            document_repository=document_repository,
            chunk_repository=chunk_repository,
            conversation_repository=conversation_repository,
            message_repository=message_repository,
            user_id=user_id,
        )

        result = tool.execute({})

        print("\n=== WORKSPACE STATS ===")
        print(f"Documents:      {result.documents}")
        print(f"Chunks:         {result.chunks}")
        print(f"Conversations:  {result.conversations}")
        print(f"Messages:       {result.messages}")

    finally:
        db.close()


if __name__ == "__main__":
    main()