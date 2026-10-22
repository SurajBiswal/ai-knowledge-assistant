"""SQLAlchemy model for one user conversation.

``ChatService`` and ``ConversationRepository`` create and manage these records.
Each conversation belongs to one User and contains an ordered list of Messages.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.message import Message

class Conversation(Base):
    """Store the title, mode, owner, and messages for one chat thread."""

    __tablename__ = "conversations"

    # Unique conversation ID used in API URLs and message foreign keys.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Owner of the conversation; API routes compare this with the JWT user.
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    # Name shown in the conversation list and optionally generated from chat.
    title: Mapped[str] = mapped_column(
        String(500),
        default="New Chat",
        nullable=False,
    )

    # Conversation behavior selected when the conversation is created.
    mode: Mapped[str] = mapped_column(
        String(50),
        default="chat",
        nullable=False,
    )

    # Database-managed creation and last-update times returned by the API.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # SQLAlchemy link back to the User that owns this conversation.
    user: Mapped["User"] = relationship(
    back_populates="conversations",
    )

    # Stored user and assistant messages; deleting the conversation removes them.
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
