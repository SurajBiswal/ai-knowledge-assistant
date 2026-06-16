import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        default="New Chat",
    )

    created_at: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )   

    updated_at: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    model: Mapped[str] = mapped_column(
        String(255),
        default="gpt-4o",
    )