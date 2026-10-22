"""Database queries for application-level LLM provider definitions.

The settings API and LLMProviderService use this repository to validate which
provider protocols exist and which ones are currently enabled.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.llm_provider import LLMProvider


class LLMProviderRepository:
    """Find shared provider definitions by ID/code or list enabled providers."""

    def __init__(self, db: Session) -> None:
        """Store the database session used for provider queries."""
        self.db = db

    def get_by_id(self, provider_id: UUID) -> LLMProvider | None:
        """Return one provider definition by UUID, or None when missing."""
        statement = select(LLMProvider).where(
            LLMProvider.id == provider_id
        )

        return self.db.scalar(statement)

    def get_by_code(self, code: str) -> LLMProvider | None:
        """Return one provider by its stable machine-readable code."""
        statement = select(LLMProvider).where(
            LLMProvider.code == code
        )

        return self.db.scalar(statement)

    def list_enabled(self) -> list[LLMProvider]:
        """Return enabled provider choices ordered for the settings UI."""
        statement = (
            select(LLMProvider)
            .where(LLMProvider.is_enabled.is_(True))
            .order_by(LLMProvider.name)
        )

        return list(self.db.scalars(statement).all())
