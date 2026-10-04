from cryptography.fernet import Fernet
import pytest

from app.services.credential_encryption_service import (
    CredentialEncryptionService,
)


def test_encrypt_and_decrypt_round_trip() -> None:
    key = Fernet.generate_key().decode()

    service = CredentialEncryptionService(
        encryption_key=key,
    )

    plaintext = "test-api-key-12345"

    encrypted = service.encrypt(plaintext)
    decrypted = service.decrypt(encrypted)

    assert decrypted == plaintext
    assert encrypted != plaintext


def test_encrypted_value_is_not_plaintext() -> None:
    key = Fernet.generate_key().decode()

    service = CredentialEncryptionService(
        encryption_key=key,
    )

    plaintext = "super-secret-api-key"

    encrypted = service.encrypt(plaintext)

    assert plaintext not in encrypted


def test_same_plaintext_produces_different_ciphertext() -> None:
    key = Fernet.generate_key().decode()

    service = CredentialEncryptionService(
        encryption_key=key,
    )

    plaintext = "same-api-key"

    encrypted_1 = service.encrypt(plaintext)
    encrypted_2 = service.encrypt(plaintext)

    assert encrypted_1 != encrypted_2


def test_empty_value_cannot_be_encrypted() -> None:
    key = Fernet.generate_key().decode()

    service = CredentialEncryptionService(
        encryption_key=key,
    )

    with pytest.raises(ValueError):
        service.encrypt("")


def test_empty_encrypted_value_cannot_be_decrypted() -> None:
    key = Fernet.generate_key().decode()

    service = CredentialEncryptionService(
        encryption_key=key,
    )

    with pytest.raises(ValueError):
        service.decrypt("")


def test_invalid_encrypted_value_fails() -> None:
    key = Fernet.generate_key().decode()

    service = CredentialEncryptionService(
        encryption_key=key,
    )

    with pytest.raises(ValueError):
        service.decrypt("not-a-valid-encrypted-value")


def test_wrong_key_cannot_decrypt() -> None:
    key_1 = Fernet.generate_key().decode()
    key_2 = Fernet.generate_key().decode()

    service_1 = CredentialEncryptionService(
        encryption_key=key_1,
    )

    service_2 = CredentialEncryptionService(
        encryption_key=key_2,
    )

    encrypted = service_1.encrypt("secret-api-key")

    with pytest.raises(ValueError):
        service_2.decrypt(encrypted)