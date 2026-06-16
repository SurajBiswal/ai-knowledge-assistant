import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False,
    )

    role: Mapped[str]

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at : Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    token_count: Mapped[int] = mapped_column(
        nullable=False, 
    )
    
    sources: Mapped[list] = mapped_column(
        nullable=False,
    )