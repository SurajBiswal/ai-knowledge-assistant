"""Runtime selection of an authenticated user's active tool-calling LLM."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.llm.base import LLMProviderError, ToolCallingLLM
from app.llm.openai_compatible import OpenAICompatibleToolCallingLLM
from app.repositories.llm_provider_profile_repository import (
    LLMProviderProfileRepository,
)
from app.repositories.llm_provider_repository import LLMProviderRepository
from app.services.credential_encryption_service import (
    CredentialEncryptionService,
)


class LLMProviderFactory:
    """Resolve the model client for one authenticated user at runtime.

    The factory is intentionally request-scoped. It reads only the active
    profile belonging to ``user_id`` and decrypts that profile's credential
    immediately before constructing the client. It never returns credentials
    or stores them in application state.

    A user must have a successfully tested, active profile. The application
    never falls back to a shared/system LLM for chat requests.
    """

    def __init__(
        self,
        *,
        db: Session,
        profile_repository: LLMProviderProfileRepository | None = None,
        provider_repository: LLMProviderRepository | None = None,
        credential_encryption_service: CredentialEncryptionService | None = None,
        openai_compatible_factory: Callable[..., ToolCallingLLM] = (
            OpenAICompatibleToolCallingLLM
        ),
    ) -> None:
        self.profile_repository = (
            profile_repository or LLMProviderProfileRepository(db)
        )
        self.provider_repository = (
            provider_repository or LLMProviderRepository(db)
        )
        self._credential_encryption_service = credential_encryption_service
        self._openai_compatible_factory = openai_compatible_factory

    def create_for_user(self, *, user_id: UUID) -> ToolCallingLLM:
        """Create the active LLM client for ``user_id``.

        Raises:
            LLMProviderError: If an active profile cannot be used safely.
        """
        profile = self.require_active_profile(user_id=user_id)

        return self._create_from_profile(profile)

    def require_active_profile(self, *, user_id: UUID):
        """Confirm a user may start a chat with their configured provider.

        This is deliberately credential-free so streaming endpoints can
        validate the request and return an HTTP error before sending a stream.
        """
        profile = self.profile_repository.get_active_by_user(user_id=user_id)

        if profile is None:
            raise LLMProviderError(
                "No active language-model provider is configured. Open "
                "Settings to add, test, and activate a provider before "
                "chatting."
            )

        if profile.last_test_status != "success":
            raise LLMProviderError(
                "Your active language-model provider has not passed a "
                "connection test. Open Settings and test it before chatting."
            )

        self._validate_profile_provider(profile)
        return profile

    def create_for_profile(
        self,
        *,
        profile_id: UUID,
        user_id: UUID,
    ) -> ToolCallingLLM:
        """Create a client for a user-owned profile during connection testing.

        Unlike ``create_for_user``, this supports an inactive profile because
        a profile must be tested before it can be activated.
        """
        profile = self.profile_repository.get_by_id(
            profile_id=profile_id,
            user_id=user_id,
        )
        if profile is None:
            raise LLMProviderError("LLM provider profile not found.")

        return self._create_from_profile(profile)

    def _create_from_profile(self, profile) -> ToolCallingLLM:
        self._validate_profile_provider(profile)

        try:
            api_key = self._get_encryption_service().decrypt(
                profile.encrypted_api_key
            )
            return self._openai_compatible_factory(
                base_url=profile.base_url,
                model=profile.model,
                api_key=api_key,
                timeout_seconds=profile.timeout_seconds,
            )
        except LLMProviderError:
            raise
        except Exception as exc:
            # Do not include provider configuration or credential values in
            # errors because the exception may be surfaced to an API caller.
            raise LLMProviderError(
                "Unable to create the active LLM client."
            ) from exc

    def _validate_profile_provider(self, profile) -> None:
        provider = self.provider_repository.get_by_id(profile.provider_id)
        if provider is None:
            raise LLMProviderError(
                "The active LLM provider configuration no longer exists."
            )
        if not provider.is_enabled:
            raise LLMProviderError("The active LLM provider is disabled.")

        if provider.protocol != "openai_compatible":
            raise LLMProviderError(
                "The active LLM provider protocol is not supported."
            )

    def _get_encryption_service(self) -> CredentialEncryptionService:
        # Defer configuration validation until a profile is actually used.
        if self._credential_encryption_service is None:
            self._credential_encryption_service = CredentialEncryptionService()

        return self._credential_encryption_service
