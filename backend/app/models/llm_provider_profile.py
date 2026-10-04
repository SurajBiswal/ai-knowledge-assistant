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
    __tablename__ = "llm_provider_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("llm_providers.id"),
        nullable=False,
        index=True,
    )

    profile_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    base_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    encrypted_api_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False,
    )

    structured_json_responses: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_test_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    last_test_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

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