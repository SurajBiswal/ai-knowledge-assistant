"""SQLAlchemy model for a user's saved language-model configuration.

Profiles contain the endpoint, model, encrypted credential, connection-test
state, and activation state used by ``LLMProviderFactory`` at chat runtime.
The API and service layers always scope profile access by ``user_id``.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.llm_provider import LLMProvider


class LLMProviderProfile(Base):
    """Store one user-owned configuration for an LLM endpoint."""

    __tablename__ = "llm_provider_profiles"

    # Unique profile ID used by settings endpoints.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # User who owns the profile and its encrypted API credential.
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider protocol used to construct the correct LLM adapter.
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("llm_providers.id"),
        nullable=False,
        index=True,
    )

    # User-friendly label shown in the settings screen.
    profile_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Root API address used by the OpenAI-compatible client.
    base_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    # Provider-specific model identifier sent with model requests.
    model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Encrypted user credential; APIs never return this stored value.
    encrypted_api_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Maximum number of seconds allowed for a provider request.
    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False,
    )

    # User preference for structured JSON responses when supported.
    structured_json_responses: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # True only for the profile currently selected for this user's chats.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Time and result of the most recent connection test.
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_test_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    # Safe diagnostic text stored when the latest connection test failed.
    last_test_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    # SQLAlchemy links to the owning user and provider definition.
    user: Mapped["User"] = relationship(
        back_populates="llm_provider_profiles",
    )

    provider: Mapped["LLMProvider"] = relationship(
        back_populates="profiles",
    )

    __table_args__ = (
        # One active LLM profile per user.
        Index(
            "uq_llm_provider_profiles_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=(is_active.is_(True)),
        ),

        # Useful for user profile lookups and filtering.
        Index(
            "ix_llm_provider_profiles_user_active",
            "user_id",
            "is_active",
        ),

        # Timeout must always be positive.
        CheckConstraint(
            "timeout_seconds > 0",
            name="ck_llm_provider_profiles_timeout_positive",
        ),
    )
