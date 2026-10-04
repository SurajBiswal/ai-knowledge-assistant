from __future__ import annotations

from unittest.mock import Mock
from uuid import uuid4

from cryptography.fernet import Fernet

from app.llm.base import ModelResponse
from app.models.llm_provider import LLMProvider
from app.models.llm_provider_profile import LLMProviderProfile
from app.services.credential_encryption_service import (
    CredentialEncryptionService,
)
from app.services.llm_provider_service import LLMProviderService


class FakeConnectionLLM:
    def __init__(self, *, text: str | None = "connection successful") -> None:
        self.text = text
        self.closed = False
        self.queries: list[str] = []

    def start_conversation(self, query: str):
        self.queries.append(query)
        return object()

    def generate(self, conversation, tools):
        assert tools == []
        return ModelResponse(text=self.text)

    def close(self) -> None:
        self.closed = True


def make_provider() -> LLMProvider:
    return LLMProvider(
        id=uuid4(),
        code="openai_compatible",
        name="OpenAI-compatible",
        protocol="openai_compatible",
        is_enabled=True,
    )


def make_profile(*, user_id, provider_id) -> LLMProviderProfile:
    return LLMProviderProfile(
        id=uuid4(),
        user_id=user_id,
        provider_id=provider_id,
        profile_name="Qwen Development",
        base_url="https://api.example.test/v1",
        model="qwen-test",
        encrypted_api_key="encrypted-value",
        timeout_seconds=60,
        structured_json_responses=True,
        is_active=False,
    )


def make_service(*, factory: Mock) -> LLMProviderService:
    encryption = CredentialEncryptionService(Fernet.generate_key().decode())
    service = LLMProviderService(
        db=Mock(),
        credential_encryption_service=encryption,
        llm_provider_factory=factory,
    )
    service.provider_repository = Mock()
    service.profile_repository = Mock()
    return service


def test_connection_test_persists_success_without_exposing_credentials() -> None:
    user_id = uuid4()
    provider = make_provider()
    profile = make_profile(user_id=user_id, provider_id=provider.id)
    llm = FakeConnectionLLM()
    factory = Mock()
    factory.create_for_profile.return_value = llm
    service = make_service(factory=factory)
    service.profile_repository.get_by_id.return_value = profile
    service.profile_repository.record_connection_test.return_value = profile
    service.provider_repository.get_by_id.return_value = provider

    result = service.test_profile_connection(
        profile_id=profile.id,
        user_id=user_id,
    )

    assert result.success is True
    assert result.message == "Connection successful."
    assert llm.closed is True
    factory.create_for_profile.assert_called_once_with(
        profile_id=profile.id,
        user_id=user_id,
    )
    persisted = service.profile_repository.record_connection_test.call_args.kwargs
    assert persisted["status"] == "success"
    assert persisted["error"] is None
    assert persisted["tested_at"].tzinfo is not None


def test_connection_test_persists_a_safe_failure_message() -> None:
    user_id = uuid4()
    provider = make_provider()
    profile = make_profile(user_id=user_id, provider_id=provider.id)
    factory = Mock()
    factory.create_for_profile.side_effect = RuntimeError("api-key-should-not-leak")
    service = make_service(factory=factory)
    service.profile_repository.get_by_id.return_value = profile
    service.profile_repository.record_connection_test.return_value = profile
    service.provider_repository.get_by_id.return_value = provider

    result = service.test_profile_connection(
        profile_id=profile.id,
        user_id=user_id,
    )

    assert result.success is False
    assert "api-key-should-not-leak" not in result.message
    persisted = service.profile_repository.record_connection_test.call_args.kwargs
    assert persisted["status"] == "failed"
    assert "api-key-should-not-leak" not in persisted["error"]


def test_activation_requires_a_successful_connection_test() -> None:
    user_id = uuid4()
    provider = make_provider()
    profile = make_profile(user_id=user_id, provider_id=provider.id)
    service = make_service(factory=Mock())
    service.profile_repository.get_by_id.return_value = profile
    service.provider_repository.get_by_id.return_value = provider

    try:
        service.activate_profile(profile_id=profile.id, user_id=user_id)
    except ValueError as error:
        assert "Test the LLM provider profile successfully" in str(error)
    else:
        raise AssertionError("Untested profile activation should be rejected.")

    service.profile_repository.activate.assert_not_called()


def test_connection_setting_change_invalidates_test_and_deactivates_profile() -> None:
    user_id = uuid4()
    provider = make_provider()
    profile = make_profile(user_id=user_id, provider_id=provider.id)
    profile.is_active = True
    profile.last_test_status = "success"
    service = make_service(factory=Mock())
    service.profile_repository.get_by_id.return_value = profile
    service.profile_repository.update.return_value = profile
    service.profile_repository.invalidate_connection_test.return_value = profile

    result = service.update_profile(
        profile_id=profile.id,
        user_id=user_id,
        model="qwen-next",
    )

    assert result is profile
    service.profile_repository.invalidate_connection_test.assert_called_once_with(
        profile_id=profile.id,
        user_id=user_id,
        deactivate=True,
    )
