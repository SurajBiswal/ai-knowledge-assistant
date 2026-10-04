from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from cryptography.fernet import Fernet

from app.models.llm_provider import LLMProvider
from app.models.llm_provider_profile import LLMProviderProfile
from app.services.credential_encryption_service import (
    CredentialEncryptionService,
)
from app.services.llm_provider_service import LLMProviderService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def another_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def provider() -> LLMProvider:
    provider = LLMProvider(
        id=uuid.uuid4(),
        code="openai_compatible",
        name="OpenAI-compatible",
        protocol="openai_compatible",
        is_enabled=True,
    )
    return provider


@pytest.fixture
def disabled_provider() -> LLMProvider:
    provider = LLMProvider(
        id=uuid.uuid4(),
        code="disabled_provider",
        name="Disabled Provider",
        protocol="openai_compatible",
        is_enabled=False,
    )
    return provider


@pytest.fixture
def profile(
    user_id: uuid.UUID,
    provider: LLMProvider,
) -> LLMProviderProfile:
    profile = LLMProviderProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        provider_id=provider.id,
        profile_name="My OpenAI Profile",
        base_url="https://api.example.com/v1",
        model="test-model",
        encrypted_api_key="encrypted-api-key",
        timeout_seconds=60,
        structured_json_responses=True,
        is_active=False,
    )
    return profile


@pytest.fixture
def encryption_service() -> CredentialEncryptionService:
    key = Fernet.generate_key().decode()
    return CredentialEncryptionService(
        encryption_key=key,
    )


@pytest.fixture
def service(
    encryption_service: CredentialEncryptionService,
) -> LLMProviderService:
    """
    Build the service without a real database.

    Repository dependencies are replaced with mocks so these tests
    focus only on service/business logic.
    """
    db = Mock()

    service = LLMProviderService(
        db=db,
        credential_encryption_service=encryption_service,
    )

    service.provider_repository = Mock()
    service.profile_repository = Mock()

    return service


# ---------------------------------------------------------------------------
# Create profile
# ---------------------------------------------------------------------------


def test_create_profile_encrypts_api_key(
    service: LLMProviderService,
    encryption_service: CredentialEncryptionService,
    user_id: uuid.UUID,
    provider: LLMProvider,
) -> None:
    service.provider_repository.get_by_id.return_value = provider

    created_profile = LLMProviderProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        provider_id=provider.id,
        profile_name="My DeepSeek",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        encrypted_api_key="placeholder",
        timeout_seconds=60,
        structured_json_responses=True,
        is_active=False,
    )

    service.profile_repository.create.return_value = created_profile

    result = service.create_profile(
        user_id=user_id,
        provider_id=provider.id,
        profile_name="My DeepSeek",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key="test-api-key-123",
    )

    assert result is created_profile

    service.profile_repository.create.assert_called_once()

    call_kwargs = service.profile_repository.create.call_args.kwargs

    assert call_kwargs["user_id"] == user_id
    assert call_kwargs["provider_id"] == provider.id
    assert call_kwargs["profile_name"] == "My DeepSeek"
    assert call_kwargs["base_url"] == "https://api.deepseek.com/v1"
    assert call_kwargs["model"] == "deepseek-chat"

    encrypted_api_key = call_kwargs["encrypted_api_key"]

    assert encrypted_api_key != "test-api-key-123"
    assert "test-api-key-123" not in encrypted_api_key

    assert (
        encryption_service.decrypt(encrypted_api_key)
        == "test-api-key-123"
    )

    # Creation must happen inactive first.
    assert call_kwargs["is_active"] is False


def test_create_profile_rejects_invalid_provider(
    service: LLMProviderService,
    user_id: uuid.UUID,
) -> None:
    provider_id = uuid.uuid4()

    service.provider_repository.get_by_id.return_value = None

    with pytest.raises(
        ValueError,
        match="LLM provider not found",
    ):
        service.create_profile(
            user_id=user_id,
            provider_id=provider_id,
            profile_name="Test Profile",
            base_url="https://api.example.com/v1",
            model="test-model",
            api_key="test-api-key",
        )

    service.profile_repository.create.assert_not_called()


def test_create_profile_rejects_disabled_provider(
    service: LLMProviderService,
    user_id: uuid.UUID,
    disabled_provider: LLMProvider,
) -> None:
    service.provider_repository.get_by_id.return_value = (
        disabled_provider
    )

    with pytest.raises(
        ValueError,
        match="LLM provider is disabled",
    ):
        service.create_profile(
            user_id=user_id,
            provider_id=disabled_provider.id,
            profile_name="Test Profile",
            base_url="https://api.example.com/v1",
            model="test-model",
            api_key="test-api-key",
        )

    service.profile_repository.create.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("profile_name", ""),
        ("base_url", ""),
        ("model", ""),
        ("api_key", ""),
    ],
)
def test_create_profile_rejects_empty_required_values(
    service: LLMProviderService,
    user_id: uuid.UUID,
    provider: LLMProvider,
    field: str,
    value: str,
) -> None:
    service.provider_repository.get_by_id.return_value = provider

    values = {
        "profile_name": "Test Profile",
        "base_url": "https://api.example.com/v1",
        "model": "test-model",
        "api_key": "test-api-key",
    }

    values[field] = value

    with pytest.raises(ValueError):
        service.create_profile(
            user_id=user_id,
            provider_id=provider.id,
            profile_name=values["profile_name"],
            base_url=values["base_url"],
            model=values["model"],
            api_key=values["api_key"],
        )

    service.profile_repository.create.assert_not_called()


def test_create_profile_rejects_whitespace_required_values(
    service: LLMProviderService,
    user_id: uuid.UUID,
    provider: LLMProvider,
) -> None:
    service.provider_repository.get_by_id.return_value = provider

    with pytest.raises(ValueError):
        service.create_profile(
            user_id=user_id,
            provider_id=provider.id,
            profile_name="   ",
            base_url="https://api.example.com/v1",
            model="test-model",
            api_key="test-api-key",
        )

    service.profile_repository.create.assert_not_called()


def test_create_profile_rejects_invalid_timeout(
    service: LLMProviderService,
    user_id: uuid.UUID,
    provider: LLMProvider,
) -> None:
    service.provider_repository.get_by_id.return_value = provider

    with pytest.raises(
        ValueError,
        match="Timeout must be greater than zero",
    ):
        service.create_profile(
            user_id=user_id,
            provider_id=provider.id,
            profile_name="Test Profile",
            base_url="https://api.example.com/v1",
            model="test-model",
            api_key="test-api-key",
            timeout_seconds=0,
        )

    service.profile_repository.create.assert_not_called()


def test_create_active_profile_is_rejected_until_connection_test(
    service: LLMProviderService,
    user_id: uuid.UUID,
    provider: LLMProvider,
) -> None:
    service.provider_repository.get_by_id.return_value = provider

    created_profile = LLMProviderProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        provider_id=provider.id,
        profile_name="Active Profile",
        base_url="https://api.example.com/v1",
        model="test-model",
        encrypted_api_key="encrypted",
        timeout_seconds=60,
        structured_json_responses=True,
        is_active=False,
    )

    with pytest.raises(
        ValueError,
        match="pass a connection test before activation",
    ):
        service.create_profile(
            user_id=user_id,
            provider_id=provider.id,
            profile_name="Active Profile",
            base_url="https://api.example.com/v1",
            model="test-model",
            api_key="test-api-key",
            is_active=True,
        )

    service.profile_repository.create.assert_not_called()
    service.profile_repository.activate.assert_not_called()


# ---------------------------------------------------------------------------
# List / Get
# ---------------------------------------------------------------------------


def test_list_profiles_is_user_scoped(
    service: LLMProviderService,
    user_id: uuid.UUID,
    profile: LLMProviderProfile,
) -> None:
    service.profile_repository.list_by_user.return_value = [
        profile
    ]

    result = service.list_profiles(
        user_id=user_id,
    )

    assert result == [profile]

    service.profile_repository.list_by_user.assert_called_once_with(
        user_id=user_id,
    )


def test_get_profile_is_user_scoped(
    service: LLMProviderService,
    user_id: uuid.UUID,
    profile: LLMProviderProfile,
) -> None:
    service.profile_repository.get_by_id.return_value = profile

    result = service.get_profile(
        profile_id=profile.id,
        user_id=user_id,
    )

    assert result is profile

    service.profile_repository.get_by_id.assert_called_once_with(
        profile_id=profile.id,
        user_id=user_id,
    )


def test_get_profile_rejects_missing_profile(
    service: LLMProviderService,
    user_id: uuid.UUID,
) -> None:
    profile_id = uuid.uuid4()

    service.profile_repository.get_by_id.return_value = None

    with pytest.raises(
        ValueError,
        match="LLM provider profile not found",
    ):
        service.get_profile(
            profile_id=profile_id,
            user_id=user_id,
        )


# ---------------------------------------------------------------------------
# Active profile
# ---------------------------------------------------------------------------


def test_get_active_profile_is_user_scoped(
    service: LLMProviderService,
    user_id: uuid.UUID,
    profile: LLMProviderProfile,
) -> None:
    profile.is_active = True

    service.profile_repository.get_active_by_user.return_value = profile

    result = service.get_active_profile(
        user_id=user_id,
    )

    assert result is profile

    service.profile_repository.get_active_by_user.assert_called_once_with(
        user_id=user_id,
    )


def test_get_active_profile_returns_none_when_not_configured(
    service: LLMProviderService,
    user_id: uuid.UUID,
) -> None:
    service.profile_repository.get_active_by_user.return_value = None

    result = service.get_active_profile(
        user_id=user_id,
    )

    assert result is None


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def test_update_profile_encrypts_new_api_key(
    service: LLMProviderService,
    encryption_service: CredentialEncryptionService,
    user_id: uuid.UUID,
    profile: LLMProviderProfile,
) -> None:
    service.profile_repository.get_by_id.return_value = profile
    service.provider_repository.get_by_id.return_value = Mock(
        id=profile.provider_id,
        is_enabled=True,
    )
    service.profile_repository.update.return_value = profile
    service.profile_repository.invalidate_connection_test.return_value = profile

    result = service.update_profile(
        profile_id=profile.id,
        user_id=user_id,
        api_key="new-test-api-key",
    )

    assert result is profile

    call_kwargs = service.profile_repository.update.call_args.kwargs

    encrypted_api_key = call_kwargs["encrypted_api_key"]

    assert encrypted_api_key != "new-test-api-key"
    assert "new-test-api-key" not in encrypted_api_key

    assert (
        encryption_service.decrypt(encrypted_api_key)
        == "new-test-api-key"
    )
    service.profile_repository.invalidate_connection_test.assert_called_once_with(
        profile_id=profile.id,
        user_id=user_id,
        deactivate=False,
    )


def test_update_profile_keeps_existing_api_key_when_not_provided(
    service: LLMProviderService,
    user_id: uuid.UUID,
    profile: LLMProviderProfile,
) -> None:
    service.profile_repository.get_by_id.return_value = profile
    service.profile_repository.update.return_value = profile

    service.update_profile(
        profile_id=profile.id,
        user_id=user_id,
        model="new-model",
    )

    call_kwargs = service.profile_repository.update.call_args.kwargs

    assert call_kwargs["model"] == "new-model"
    assert call_kwargs["encrypted_api_key"] is None


def test_update_profile_rejects_invalid_provider(
    service: LLMProviderService,
    user_id: uuid.UUID,
    profile: LLMProviderProfile,
) -> None:
    service.profile_repository.get_by_id.return_value = profile
    service.provider_repository.get_by_id.return_value = None

    with pytest.raises(
        ValueError,
        match="LLM provider not found",
    ):
        service.update_profile(
            profile_id=profile.id,
            user_id=user_id,
            provider_id=uuid.uuid4(),
        )

    service.profile_repository.update.assert_not_called()


def test_update_profile_rejects_invalid_timeout(
    service: LLMProviderService,
    user_id: uuid.UUID,
    profile: LLMProviderProfile,
) -> None:
    service.profile_repository.get_by_id.return_value = profile

    with pytest.raises(
        ValueError,
        match="Timeout must be greater than zero",
    ):
        service.update_profile(
            profile_id=profile.id,
            user_id=user_id,
            timeout_seconds=0,
        )

    service.profile_repository.update.assert_not_called()


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_profile_rejects_active_profile(
    service: LLMProviderService,
    user_id: uuid.UUID,
    profile: LLMProviderProfile,
) -> None:
    profile.is_active = True

    service.profile_repository.get_by_id.return_value = profile

    with pytest.raises(
        ValueError,
        match="Cannot delete the active LLM provider profile",
    ):
        service.delete_profile(
            profile_id=profile.id,
            user_id=user_id,
        )

    service.profile_repository.delete.assert_not_called()


def test_delete_profile_works_for_inactive_profile(
    service: LLMProviderService,
    user_id: uuid.UUID,
    profile: LLMProviderProfile,
) -> None:
    profile.is_active = False

    service.profile_repository.get_by_id.return_value = profile
    service.profile_repository.delete.return_value = True

    result = service.delete_profile(
        profile_id=profile.id,
        user_id=user_id,
    )

    assert result is None

    service.profile_repository.delete.assert_called_once_with(
        profile_id=profile.id,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# Activate
# ---------------------------------------------------------------------------


def test_activate_profile_deactivates_previous_profile(
    service: LLMProviderService,
    user_id: uuid.UUID,
    profile: LLMProviderProfile,
) -> None:
    service.profile_repository.get_by_id.return_value = profile

    service.provider_repository.get_by_id.return_value = Mock(
        id=profile.provider_id,
        is_enabled=True,
    )

    profile.is_active = True
    profile.last_test_status = "success"

    service.profile_repository.activate.return_value = profile

    result = service.activate_profile(
        profile_id=profile.id,
        user_id=user_id,
    )

    assert result is profile

    service.profile_repository.activate.assert_called_once_with(
        profile_id=profile.id,
        user_id=user_id,
    )


def test_activate_profile_is_user_scoped(
    service: LLMProviderService,
    another_user_id: uuid.UUID,
    profile: LLMProviderProfile,
) -> None:
    # Repository should return None when the profile does not belong
    # to the requesting user.
    service.profile_repository.get_by_id.return_value = None

    with pytest.raises(
        ValueError,
        match="LLM provider profile not found",
    ):
        service.activate_profile(
            profile_id=profile.id,
            user_id=another_user_id,
        )

    service.profile_repository.activate.assert_not_called()


def test_activate_profile_rejects_disabled_provider(
    service: LLMProviderService,
    user_id: uuid.UUID,
    profile: LLMProviderProfile,
    disabled_provider: LLMProvider,
) -> None:
    profile.provider_id = disabled_provider.id

    service.profile_repository.get_by_id.return_value = profile
    service.provider_repository.get_by_id.return_value = (
        disabled_provider
    )

    with pytest.raises(
        ValueError,
        match="LLM provider is disabled",
    ):
        service.activate_profile(
            profile_id=profile.id,
            user_id=user_id,
        )

    service.profile_repository.activate.assert_not_called()
