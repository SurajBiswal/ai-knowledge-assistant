"""Encrypt and decrypt user-owned API credentials.

LLMProviderService encrypts keys before saving profiles. LLMProviderFactory
decrypts them only while creating a runtime client. API responses never expose
the encrypted value or plaintext key.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class CredentialEncryptionService:
    """
    Provides authenticated symmetric encryption for user credentials.

    The encryption key is application-level configuration and must never
    be the user's API key.
    """

    def __init__(self, encryption_key: str | None = None) -> None:
        """Create a Fernet cipher from an explicit key or application setting."""
        key = encryption_key or settings.CREDENTIAL_ENCRYPTION_KEY

        if not key:
            raise ValueError(
                "CREDENTIAL_ENCRYPTION_KEY is not configured."
            )

        try:
            self._fernet = Fernet(key.encode())
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "CREDENTIAL_ENCRYPTION_KEY is not a valid Fernet key."
            ) from exc

    def encrypt(self, value: str) -> str:
        """Return a database-safe encrypted string for a plaintext credential."""
        if not value or not value.strip():
            raise ValueError("Credential cannot be empty.")

        encrypted = self._fernet.encrypt(
            value.encode("utf-8")
        )

        return encrypted.decode("utf-8")

    def decrypt(self, encrypted_value: str) -> str:
        """Return plaintext or raise ValueError when the value/key is invalid."""
        if not encrypted_value or not encrypted_value.strip():
            raise ValueError("Encrypted credential cannot be empty.")

        try:
            decrypted = self._fernet.decrypt(
                encrypted_value.encode("utf-8")
            )
        except InvalidToken as exc:
            raise ValueError(
                "Unable to decrypt credential. "
                "The value may be invalid or the encryption key may differ."
            ) from exc

        return decrypted.decode("utf-8")
