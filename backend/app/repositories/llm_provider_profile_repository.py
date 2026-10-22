"""Database operations for user-owned LLM provider profiles.

Every lookup includes ``user_id`` so one user cannot read or modify another
user's endpoint or encrypted credential. LLMProviderService owns validation and
transaction decisions; this repository performs the database operations.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update as sql_update
from sqlalchemy.orm import Session

from app.models.llm_provider_profile import LLMProviderProfile


class LLMProviderProfileRepository:
    """Store and retrieve provider profiles while enforcing user scope."""

    def __init__(self, db: Session) -> None:
        """Store the database session used by all profile operations."""
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        provider_id: UUID,
        profile_name: str,
        base_url: str,
        model: str,
        encrypted_api_key: str,
        timeout_seconds: int = 60,
        structured_json_responses: bool = True,
        is_active: bool = False,
    ) -> LLMProviderProfile:
        """Add a new profile with an encrypted key to the current transaction."""
        profile = LLMProviderProfile(
            user_id=user_id,
            provider_id=provider_id,
            profile_name=profile_name,
            base_url=base_url,
            model=model,
            encrypted_api_key=encrypted_api_key,
            timeout_seconds=timeout_seconds,
            structured_json_responses=structured_json_responses,
            is_active=is_active,
        )

        self.db.add(profile)
        self.db.flush()

        return profile

    def get_by_id(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
    ) -> LLMProviderProfile | None:
        """Return a profile only when both profile ID and owner match."""
        statement = select(LLMProviderProfile).where(
            LLMProviderProfile.id == profile_id,
            LLMProviderProfile.user_id == user_id,
        )

        return self.db.scalar(statement)

    def list_by_user(
        self,
        *,
        user_id: UUID,
    ) -> list[LLMProviderProfile]:
        """List one user's profiles with the active profile first."""
        statement = (
            select(LLMProviderProfile)
            .where(LLMProviderProfile.user_id == user_id)
            .order_by(
                LLMProviderProfile.is_active.desc(),
                LLMProviderProfile.created_at.desc(),
            )
        )

        return list(self.db.scalars(statement).all())

    def get_active_by_user(
        self,
        *,
        user_id: UUID,
    ) -> LLMProviderProfile | None:
        """Return the single active profile selected for this user's chats."""
        statement = select(LLMProviderProfile).where(
            LLMProviderProfile.user_id == user_id,
            LLMProviderProfile.is_active.is_(True),
        )

        return self.db.scalar(statement)

    def update(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
        profile_name: str | None = None,
        provider_id: UUID | None = None,
        base_url: str | None = None,
        model: str | None = None,
        encrypted_api_key: str | None = None,
        timeout_seconds: int | None = None,
        structured_json_responses: bool | None = None,
        last_tested_at: datetime | None = None,
        last_test_status: str | None = None,
        last_test_error: str | None = None,
    ) -> LLMProviderProfile | None:
        """Apply supplied profile fields and leave omitted fields unchanged."""
        profile = self.get_by_id(
            profile_id=profile_id,
            user_id=user_id,
        )

        if profile is None:
            return None

        if profile_name is not None:
            profile.profile_name = profile_name

        if provider_id is not None:
            profile.provider_id = provider_id

        if base_url is not None:
            profile.base_url = base_url

        if model is not None:
            profile.model = model

        if encrypted_api_key is not None:
            profile.encrypted_api_key = encrypted_api_key

        if timeout_seconds is not None:
            profile.timeout_seconds = timeout_seconds

        if structured_json_responses is not None:
            profile.structured_json_responses = structured_json_responses

        if last_tested_at is not None:
            profile.last_tested_at = last_tested_at

        if last_test_status is not None:
            profile.last_test_status = last_test_status

        if last_test_error is not None:
            profile.last_test_error = last_test_error

        self.db.flush()

        return profile

    def delete(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete an owned profile and report whether it existed."""
        profile = self.get_by_id(
            profile_id=profile_id,
            user_id=user_id,
        )

        if profile is None:
            return False

        self.db.delete(profile)
        self.db.flush()

        return True

    def activate(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
    ) -> LLMProviderProfile | None:
        """Deactivate the user's old profile and activate the requested one."""
        profile = self.get_by_id(
            profile_id=profile_id,
            user_id=user_id,
        )

        if profile is None:
            return None

        # Deactivate the user's currently active profile.
        statement = (
            sql_update(LLMProviderProfile)
            .where(
                LLMProviderProfile.user_id == user_id,
                LLMProviderProfile.is_active.is_(True),
                LLMProviderProfile.id != profile_id,
            )
            .values(is_active=False)
        )

        self.db.execute(statement)

        # Activate the requested profile.
        profile.is_active = True

        self.db.flush()

        return profile

    def record_connection_test(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
        tested_at: datetime,
        status: str,
        error: str | None,
    ) -> LLMProviderProfile | None:
        """Save the latest test time, result, and safe user-visible error."""
        profile = self.get_by_id(
            profile_id=profile_id,
            user_id=user_id,
        )
        if profile is None:
            return None

        profile.last_tested_at = tested_at
        profile.last_test_status = status
        profile.last_test_error = error
        self.db.flush()
        return profile

    def invalidate_connection_test(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
        deactivate: bool,
    ) -> LLMProviderProfile | None:
        """Clear an outdated test result after connection settings change."""
        profile = self.get_by_id(
            profile_id=profile_id,
            user_id=user_id,
        )
        if profile is None:
            return None

        profile.last_tested_at = None
        profile.last_test_status = None
        profile.last_test_error = None
        if deactivate:
            profile.is_active = False

        self.db.flush()
        return profile
