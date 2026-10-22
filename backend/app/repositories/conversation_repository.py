"""Database operations for Conversation records.

ChatService calls this repository instead of writing SQL queries. Methods create,
find, rename, list, delete, and count conversations while SQLAlchemy handles the
actual PostgreSQL communication.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation


class ConversationRepository:
    """Provide conversation queries using one SQLAlchemy session."""

    def __init__(self, db: Session):
        """Store the request's database session for all repository methods."""
        self.db = db

    def create(
        self,
        user_id: UUID,
        title: str,
        mode: str = "chat",
    ) -> Conversation:
        """Create, commit, and return a conversation owned by ``user_id``."""

        conversation = Conversation(
            user_id=user_id,
            title=title,
            mode=mode,
        )

        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    def get_by_id(
        self,
        conversation_id: UUID,
    ) -> Conversation | None:
        """Return the conversation with this ID, or None when it does not exist."""

        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
        )

        result = self.db.execute(stmt)

        return result.scalar_one_or_none()

    def rename(
        self,
        conversation_id: UUID,
        title: str,
    ) -> Conversation | None:
        """Change a conversation title and return the updated record."""

        conversation = self.get_by_id(conversation_id)

        if not conversation:
            return None

        conversation.title = title
        conversation.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    def list_by_user(
        self,
        user_id: UUID,
    ) -> list[Conversation]:
        """Return one user's conversations with the newest activity first."""

        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )

        result = self.db.execute(stmt)

        return list(result.scalars().all())

    def delete(
        self,
        conversation_id: UUID,
    ) -> bool:
        """Delete a conversation by ID and report whether a record was found."""

        conversation = self.get_by_id(conversation_id)

        if not conversation:
            return False

        self.db.delete(conversation)
        self.db.commit()

        return True

    def count_by_user(self, user_id: UUID) -> int:
        """Return the number of conversations owned by a user."""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.user_id == user_id)
        )

        return int(self.db.execute(stmt).scalar_one())
