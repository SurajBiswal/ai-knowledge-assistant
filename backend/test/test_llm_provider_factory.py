from __future__ import annotations

from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.llm.base import LLMProviderError
from app.llm.factory import LLMProviderFactory
from app.models.llm_provider import LLMProvider
from app.models.llm_provider_profile import LLMProviderProfile


def make_provider(*, protocol: str = "openai_compatible") -> LLMProvider:
    return LLMProvider(
        id=uuid4(),
        code="openai_compatible",
        name="OpenAI-compatible",
        protocol=protocol,
        is_enabled=True,
    )


def make_profile(
    *,
    user_id,
    provider_id,
) -> LLMProviderProfile:
    return LLMProviderProfile(
        id=uuid4(),
        user_id=user_id,
        provider_id=provider_id,
        profile_name="Qwen Production",
        base_url="https://api.example.test/v1",
        model="qwen-test",
        encrypted_api_key="encrypted-value",
        timeout_seconds=45,
        structured_json_responses=True,
        is_active=True,
        last_test_status="success",
    )


def make_factory(*, openai_client, encryption_service):
    profile_repository = Mock()
    provider_repository = Mock()
    factory = LLMProviderFactory(
        db=Mock(),
        profile_repository=profile_repository,
        provider_repository=provider_repository,
        credential_encryption_service=encryption_service,
        openai_compatible_factory=openai_client,
    )
    return factory, profile_repository, provider_repository


def test_factory_requires_an_active_profile() -> None:
    factory, profiles, providers = make_factory(
        openai_client=Mock(),
        encryption_service=Mock(),
    )

    user_id = uuid4()
    profiles.get_active_by_user.return_value = None

    with pytest.raises(LLMProviderError, match="No active language-model provider"):
        factory.create_for_user(user_id=user_id)

    profiles.get_active_by_user.assert_called_once_with(user_id=user_id)
    providers.get_by_id.assert_not_called()


def test_factory_builds_openai_compatible_client_from_active_profile() -> None:
    user_id = uuid4()
    provider = make_provider()
    profile = make_profile(user_id=user_id, provider_id=provider.id)
    encryption_service = Mock()
    encryption_service.decrypt.return_value = "decrypted-user-key"
    openai_instance = Mock()
    openai_factory = Mock(return_value=openai_instance)

    factory, profiles, providers = make_factory(
        openai_client=openai_factory,
        encryption_service=encryption_service,
    )
    profiles.get_active_by_user.return_value = profile
    providers.get_by_id.return_value = provider

    result = factory.create_for_user(user_id=user_id)

    assert result is openai_instance
    encryption_service.decrypt.assert_called_once_with("encrypted-value")
    openai_factory.assert_called_once_with(
        base_url="https://api.example.test/v1",
        model="qwen-test",
        api_key="decrypted-user-key",
        timeout_seconds=45,
    )


@pytest.mark.parametrize(
    ("provider_exists", "is_enabled", "protocol", "error"),
    [
        (False, True, "openai_compatible", "no longer exists"),
        (True, False, "openai_compatible", "is disabled"),
        (True, True, "unknown", "not supported"),
    ],
)
def test_factory_rejects_invalid_active_provider(
    provider_exists: bool,
    is_enabled: bool,
    protocol: str,
    error: str,
) -> None:
    user_id = uuid4()
    provider = make_provider(protocol=protocol)
    provider.is_enabled = is_enabled
    profile = make_profile(user_id=user_id, provider_id=provider.id)
    encryption_service = Mock()

    factory, profiles, providers = make_factory(
        openai_client=Mock(),
        encryption_service=encryption_service,
    )
    profiles.get_active_by_user.return_value = profile
    providers.get_by_id.return_value = provider if provider_exists else None

    with pytest.raises(LLMProviderError, match=error):
        factory.create_for_user(user_id=user_id)

    encryption_service.decrypt.assert_not_called()


def test_factory_masks_credential_decryption_failure() -> None:
    user_id = uuid4()
    provider = make_provider()
    profile = make_profile(user_id=user_id, provider_id=provider.id)
    encryption_service = Mock()
    encryption_service.decrypt.side_effect = ValueError("secret failure")

    factory, profiles, providers = make_factory(
        openai_client=Mock(),
        encryption_service=encryption_service,
    )
    profiles.get_active_by_user.return_value = profile
    providers.get_by_id.return_value = provider

    with pytest.raises(LLMProviderError, match="Unable to create") as error:
        factory.create_for_user(user_id=user_id)

    assert "secret failure" not in str(error.value)
