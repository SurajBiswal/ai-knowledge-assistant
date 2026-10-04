from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.llm_provider import LLMProvider


class LLMProviderRepository:
    """Repository for application-level LLM provider definitions."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, provider_id: UUID) -> LLMProvider | None:
        statement = select(LLMProvider).where(
            LLMProvider.id == provider_id
        )

        return self.db.scalar(statement)

    def get_by_code(self, code: str) -> LLMProvider | None:
        statement = select(LLMProvider).where(
            LLMProvider.code == code
        )

        return self.db.scalar(statement)

    def list_enabled(self) -> list[LLMProvider]:
        statement = (
            select(LLMProvider)
            .where(LLMProvider.is_enabled.is_(True))
            .order_by(LLMProvider.name)
        )

        return list(self.db.scalars(statement).all())