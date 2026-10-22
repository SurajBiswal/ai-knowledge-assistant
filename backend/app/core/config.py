"""Load application settings from environment variables.

Other modules import ``settings`` for API configuration and ``DATABASE_URL``
for SQLAlchemy. User-owned LLM keys are not stored here; they are encrypted in
provider profiles and decrypted only when a client is created.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Read-only application-wide values loaded when this module is imported."""

    # Fallback Gemini key used by older Gemini-specific services.
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Key used by WebSearchService when the web_search native tool runs.
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    # Application secret used to encrypt and decrypt user-owned provider keys.
    CREDENTIAL_ENCRYPTION_KEY = os.getenv(
        "CREDENTIAL_ENCRYPTION_KEY"
    )

    # Secret and algorithm used by security.py to sign and verify JWT tokens.
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY"
    )

    JWT_ALGORITHM = os.getenv(
        "JWT_ALGORITHM"
    )

    # Number of minutes a login token remains valid.
    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            60,
        )
    )

    # This is an operator assertion, not an application SSRF bypass. Keep it
    # false unless deployment egress rules block private/internal destinations.
    MCP_REMOTE_HTTP_EGRESS_PROTECTED = os.getenv(
        "MCP_REMOTE_HTTP_EGRESS_PROTECTED",
        "false",
    ).strip().lower() in {"1", "true", "yes", "on"}

# Shared settings object imported by services and security helpers.
settings = Settings()

# Connection string used by database/session.py to create the SQLAlchemy engine.
DATABASE_URL = os.getenv("DATABASE_URL")
