"""SQLAlchemy model for messages stored inside conversations.

``MessageRepository`` saves user questions and assistant answers. ChatService
loads recent messages for history and returns them through conversation APIs.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Message(Base):
    """Represent one user or assistant message in a conversation."""

    __tablename__ = "messages"

    # Unique database identifier for this message.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Conversation that contains the message.
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False,
    )

    # Speaker label used by chat history, such as user or assistant.
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Text displayed in the chat interface and passed to model history.
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Stored token total for usage tracking; defaults to zero when not counted.
    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # JSON source details attached to grounded answers, or an empty list.
    sources: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    # Time the database stored this message.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # SQLAlchemy link back to the containing Conversation.
    conversation: Mapped["Conversation"] = relationship(
    back_populates="messages",
)
