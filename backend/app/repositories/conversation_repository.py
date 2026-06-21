from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation


class ConversationRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: UUID,
        title: str,
        mode: str = "chat",
    ) -> Conversation:

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

        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
        )

        result = self.db.execute(stmt)

        return result.scalar_one_or_none()

    def list_by_user(
        self,
        user_id: UUID,
    ) -> list[Conversation]:

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

        conversation = self.get_by_id(conversation_id)

        if not conversation:
            return False

        self.db.delete(conversation)
        self.db.commit()

        return True