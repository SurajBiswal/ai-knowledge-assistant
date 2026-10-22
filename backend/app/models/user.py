"""SQLAlchemy model for application users.

A User owns conversations, uploaded documents, LLM provider profiles, and MCP
connection definitions. Authentication services create and find users through
``UserRepository``.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.document import Document
    from app.models.llm_provider_profile import LLMProviderProfile
    from app.models.mcp_connection import MCPConnection

class User(Base):
    """Represent one registered user and the records that belong to them."""

    __tablename__ = "users"

    # Primary identifier used by JWTs and all user-owned database records.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Display name returned by authentication endpoints.
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Unique login address used by AuthService to find the account.
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    # Irreversible password hash; the original password is never stored.
    password_hash: Mapped[str] = mapped_column(
        nullable=False,
    )

    # Database-managed creation and last-update times.
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

    # Conversations created by this user; deleting the user removes them.
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Files uploaded by this user; repositories use user_id for isolation.
    documents: Mapped[list["Document"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Saved model configurations owned by this user.
    llm_provider_profiles: Mapped[list["LLMProviderProfile"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # MCP connection definitions and encrypted credentials owned by this user.
    mcp_connections: Mapped[list["MCPConnection"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
