from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from typing import Any

from app.models.message import Message
from app.models.conversation import Conversation

class MessageRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        token_count: int = 0,
        sources: list[dict[str, Any]] | None = None,
    ) -> Message:

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            token_count=token_count,
            sources=sources or [],
        )

        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        return message

    def list_by_conversation(
        self,
        conversation_id: UUID,
    ) -> list[Message]:

        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id
            )
            .order_by(Message.created_at.asc())
        )

        result = self.db.execute(stmt)

        return list(result.scalars().all())

    def get_last_n_messages(
        self,
        conversation_id: UUID,
        limit: int = 10,
    ) -> list[Message]:

        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )

        result = self.db.execute(stmt)

        messages = list(result.scalars().all())

        return list(reversed(messages))

    def count_by_user(self, user_id: UUID) -> int:
        """Return the number of messages in a user's conversations."""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.user_id == user_id)
        )

        return int(self.db.execute(stmt).scalar_one())
