from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID
import httpx

from sqlalchemy.orm import Session

from app.models.llm_provider import LLMProvider
from app.models.llm_provider_profile import LLMProviderProfile
from app.repositories.llm_provider_profile_repository import (
    LLMProviderProfileRepository,
)
from app.repositories.llm_provider_repository import (
    LLMProviderRepository,
)
from app.services.credential_encryption_service import (
    CredentialEncryptionService,
)
from app.llm.factory import LLMProviderFactory


@dataclass(frozen=True, slots=True)
class ProviderConnectionTestResult:
    """Safe outcome of testing a saved provider profile."""

    success: bool
    message: str


class LLMProviderService:
    """
    Business logic for user-specific LLM provider profiles.

    Responsibilities:
    - Validate providers
    - Enforce user ownership
    - Encrypt API credentials
    - Manage profile lifecycle
    - Manage active-profile rules

    This service does not expose API keys to callers.
    """

    def __init__(
        self,
        db: Session,
        credential_encryption_service: CredentialEncryptionService | None = None,
        llm_provider_factory: LLMProviderFactory | None = None,
    ) -> None:
        self.db = db

        self.provider_repository = LLMProviderRepository(db)
        self.profile_repository = LLMProviderProfileRepository(db)

        self.credential_encryption_service = (
            credential_encryption_service
            or CredentialEncryptionService()
        )
        self.llm_provider_factory = (
            llm_provider_factory
            or LLMProviderFactory(
                db=db,
                credential_encryption_service=(
                    self.credential_encryption_service
                ),
            )
        )

    # ---------------------------------------------------------
    # Provider validation
    # ---------------------------------------------------------

    def _get_valid_provider(
        self,
        *,
        provider_id: UUID,
    ) -> LLMProvider:
        provider = self.provider_repository.get_by_id(provider_id)

        if provider is None:
            raise ValueError("LLM provider not found.")

        if not provider.is_enabled:
            raise ValueError("LLM provider is disabled.")

        return provider

    # ---------------------------------------------------------
    # Create
    # ---------------------------------------------------------

    def create_profile(
        self,
        *,
        user_id: UUID,
        provider_id: UUID,
        profile_name: str,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: int = 60,
        structured_json_responses: bool = True,
        is_active: bool = False,
    ) -> LLMProviderProfile:

        if is_active:
            raise ValueError(
                "Profiles must pass a connection test before activation."
            )

        # Basic validation
        if not profile_name.strip():
            raise ValueError("Profile name cannot be empty.")

        if not base_url.strip():
            raise ValueError("Base URL cannot be empty.")

        if not model.strip():
            raise ValueError("Model cannot be empty.")

        if not api_key.strip():
            raise ValueError("API key cannot be empty.")

        if timeout_seconds <= 0:
            raise ValueError("Timeout must be greater than zero.")

        # Validate provider
        self._get_valid_provider(
            provider_id=provider_id,
        )

        # Encrypt user API key before persistence
        encrypted_api_key = (
            self.credential_encryption_service.encrypt(api_key)
        )

        # Create database record
        profile = self.profile_repository.create(
            user_id=user_id,
            provider_id=provider_id,
            profile_name=profile_name.strip(),
            base_url=base_url.strip(),
            model=model.strip(),
            encrypted_api_key=encrypted_api_key,
            timeout_seconds=timeout_seconds,
            structured_json_responses=structured_json_responses,
            is_active=False,
        )

        return profile

    # ---------------------------------------------------------
    # List
    # ---------------------------------------------------------

    def list_profiles(
        self,
        *,
        user_id: UUID,
    ) -> list[LLMProviderProfile]:

        return self.profile_repository.list_by_user(
            user_id=user_id,
        )

    # ---------------------------------------------------------
    # Get
    # ---------------------------------------------------------

    def get_profile(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
    ) -> LLMProviderProfile:

        profile = self.profile_repository.get_by_id(
            profile_id=profile_id,
            user_id=user_id,
        )

        if profile is None:
            raise ValueError("LLM provider profile not found.")

        return profile

    # ---------------------------------------------------------
    # Get active profile
    # ---------------------------------------------------------

    def get_active_profile(
        self,
        *,
        user_id: UUID,
    ) -> LLMProviderProfile | None:

        return self.profile_repository.get_active_by_user(
            user_id=user_id,
        )

    # ---------------------------------------------------------
    # Update
    # ---------------------------------------------------------

    def update_profile(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
        profile_name: str | None = None,
        provider_id: UUID | None = None,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int | None = None,
        structured_json_responses: bool | None = None,
    ) -> LLMProviderProfile:

        profile = self.get_profile(
            profile_id=profile_id,
            user_id=user_id,
        )
        previous_provider_id = profile.provider_id
        previous_base_url = profile.base_url
        previous_model = profile.model
        previous_timeout_seconds = profile.timeout_seconds
        was_active = profile.is_active

        if profile_name is not None:
            if not profile_name.strip():
                raise ValueError(
                    "Profile name cannot be empty."
                )
            profile_name = profile_name.strip()

        if base_url is not None:
            if not base_url.strip():
                raise ValueError(
                    "Base URL cannot be empty."
                )
            base_url = base_url.strip()

        if model is not None:
            if not model.strip():
                raise ValueError(
                    "Model cannot be empty."
                )
            model = model.strip()

        if api_key is not None:
            if not api_key.strip():
                raise ValueError(
                    "API key cannot be empty."
                )

            encrypted_api_key = (
                self.credential_encryption_service.encrypt(
                    api_key
                )
            )
        else:
            encrypted_api_key = None

        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError(
                "Timeout must be greater than zero."
            )

        # If provider is being changed, validate the new provider.
        if provider_id is not None:
            self._get_valid_provider(
                provider_id=provider_id,
            )

        updated_profile = self.profile_repository.update(
            profile_id=profile.id,
            user_id=user_id,
            profile_name=profile_name,
            provider_id=provider_id,
            base_url=base_url,
            model=model,
            encrypted_api_key=encrypted_api_key,
            timeout_seconds=timeout_seconds,
            structured_json_responses=structured_json_responses,
        )

        if updated_profile is None:
            # This should not normally happen because we already
            # validated ownership above.
            raise ValueError(
                "LLM provider profile could not be updated."
            )

        connection_changed = any(
            (
                provider_id is not None and provider_id != previous_provider_id,
                base_url is not None and base_url != previous_base_url,
                model is not None and model != previous_model,
                api_key is not None,
                timeout_seconds is not None
                and timeout_seconds != previous_timeout_seconds,
            )
        )

        if connection_changed:
            invalidated_profile = (
                self.profile_repository.invalidate_connection_test(
                    profile_id=profile.id,
                    user_id=user_id,
                    deactivate=was_active,
                )
            )
            if invalidated_profile is None:
                raise ValueError(
                    "LLM provider profile could not be updated."
                )
            updated_profile = invalidated_profile

        return updated_profile

    # ---------------------------------------------------------
    # Delete
    # ---------------------------------------------------------

    def delete_profile(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
    ) -> None:

        profile = self.get_profile(
            profile_id=profile_id,
            user_id=user_id,
        )

        if profile.is_active:
            raise ValueError(
                "Cannot delete the active LLM provider profile."
            )

        deleted = self.profile_repository.delete(
            profile_id=profile.id,
            user_id=user_id,
        )

        if not deleted:
            raise ValueError(
                "LLM provider profile could not be deleted."
            )

    # ---------------------------------------------------------
    # Activate
    # ---------------------------------------------------------

    def activate_profile(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
    ) -> LLMProviderProfile:

        profile = self.get_profile(
            profile_id=profile_id,
            user_id=user_id,
        )

        # Validate the provider is still enabled.
        self._get_valid_provider(
            provider_id=profile.provider_id,
        )

        if profile.last_test_status != "success":
            raise ValueError(
                "Test the LLM provider profile successfully before activating it."
            )

        activated_profile = self.profile_repository.activate(
            profile_id=profile.id,
            user_id=user_id,
        )

        if activated_profile is None:
            raise ValueError(
                "LLM provider profile could not be activated."
            )

        return activated_profile

    # ---------------------------------------------------------
    # Connection test
    # ---------------------------------------------------------

    def test_profile_connection(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
    ) -> ProviderConnectionTestResult:
        """Verify a user-owned profile and persist a safe test outcome."""
        profile = self.get_profile(
            profile_id=profile_id,
            user_id=user_id,
        )
        self._get_valid_provider(provider_id=profile.provider_id)

        tested_at = datetime.now(timezone.utc)
        client = None
        try:
            client = self.llm_provider_factory.create_for_profile(
                profile_id=profile.id,
                user_id=user_id,
            )
            conversation = client.start_conversation(
                "Reply with exactly: connection successful"
            )
            response = client.generate(conversation, tools=[])
            if not response.text:
                raise RuntimeError("Provider returned no test response.")

            self._record_connection_test(
                profile_id=profile.id,
                user_id=user_id,
                tested_at=tested_at,
                status="success",
                error=None,
            )
            return ProviderConnectionTestResult(
                success=True,
                message="Connection successful.",
            )
        except Exception as exc:
            message = _safe_connection_failure_message(exc)
            self._record_connection_test(
                profile_id=profile.id,
                user_id=user_id,
                tested_at=tested_at,
                status="failed",
                error=message,
            )
            return ProviderConnectionTestResult(
                success=False,
                message=message,
            )
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()

    def _record_connection_test(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
        tested_at: datetime,
        status: str,
        error: str | None,
    ) -> None:
        profile = self.profile_repository.record_connection_test(
            profile_id=profile_id,
            user_id=user_id,
            tested_at=tested_at,
            status=status,
            error=error,
        )
        if profile is None:
            raise RuntimeError("LLM provider profile no longer exists.")


def _safe_connection_failure_message(error: Exception) -> str:
    """Map only allow-listed provider errors to safe user diagnostics."""
    for current in _exception_chain(error):
        if isinstance(current, httpx.TimeoutException):
            return "Connection timed out."

        if isinstance(current, httpx.HTTPStatusError):
            status_code = current.response.status_code
            if status_code in (401, 403):
                return (
                    f"Authentication failed (HTTP {status_code}). "
                    "Check API key."
                )
            if status_code == 404:
                return "Model or endpoint not found (HTTP 404)."
            if status_code == 429:
                return "Provider rate limit reached (HTTP 429)."
            if status_code == 503:
                return (
                    "Provider temporarily unavailable (HTTP 503). "
                    "Retry later."
                )

    return "Connection failed. Verify the base URL, model, and API key."


def _exception_chain(error: Exception):
    """Yield an exception and explicit causes without following cycles."""
    seen: set[int] = set()
    current: BaseException | None = error

    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__
