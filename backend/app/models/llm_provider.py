"""SQLAlchemy model for supported LLM communication protocols.

This table describes provider types, not individual models. For example,
``openai_compatible`` can represent OpenAI, NVIDIA, DeepSeek, Qwen, or another
endpoint that follows the same API protocol. User settings live in profiles.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.llm_provider_profile import LLMProviderProfile


class LLMProvider(Base):
    """Describe one enabled provider protocol available to all users."""

    __tablename__ = "llm_providers"

    # Stable database identifier referenced by user profiles.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Machine-readable provider code used by services and the LLM factory.
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # Human-readable label shown in provider settings.
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # API format understood by the matching LLM adapter.
    protocol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Disabled providers are hidden and rejected for new profile operations.
    is_enabled: Mapped[bool] = mapped_column(
        default=True,
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

    # User-owned configurations that use this protocol.
    profiles: Mapped[list["LLMProviderProfile"]] = relationship(
        back_populates="provider",
    )
