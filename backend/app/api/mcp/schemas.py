"""Strict public request and response models for MCP connection management.

Credential request models use ``SecretStr`` so normal representations do not
print submitted secrets. Public responses expose only whether credentials are
configured; they never contain plaintext, ciphertext, or runtime headers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr


ScalarConfigurationValue = str | int | float | bool | None


class _StrictRequest(BaseModel):
    """Reject unknown input fields at security-sensitive API boundaries."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class BearerCredentialsRequest(_StrictRequest):
    """Bearer token accepted only for an HTTP connection request."""

    token: SecretStr = Field(min_length=1, max_length=16_000)


class APIKeyHeaderCredentialsRequest(_StrictRequest):
    """API key and one allowlisted HTTP header name."""

    header_name: Literal["api-key", "x-api-key"]
    api_key: SecretStr = Field(min_length=1, max_length=16_000)


CredentialsRequest = (
    BearerCredentialsRequest | APIKeyHeaderCredentialsRequest
)


class CreateMCPConnectionRequest(_StrictRequest):
    """Validated fields used to create a disabled connection definition."""

    name: str = Field(min_length=1, max_length=100)
    transport: Literal["stdio", "streamable_http"]
    server_url: str | None = Field(default=None, max_length=2_048)
    stdio_template_code: str | None = Field(default=None, max_length=100)
    configuration: dict[str, ScalarConfigurationValue] = Field(
        default_factory=dict
    )
    auth_type: Literal["none", "bearer", "api_key_header"] = "none"
    credentials: CredentialsRequest | None = None
    timeout_seconds: int = Field(default=30, gt=0, le=300)


class UpdateMCPConnectionRequest(_StrictRequest):
    """Optional editable settings for one existing owned connection."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    transport: Literal["stdio", "streamable_http"] | None = None
    server_url: str | None = Field(default=None, max_length=2_048)
    stdio_template_code: str | None = Field(default=None, max_length=100)
    configuration: dict[str, ScalarConfigurationValue] | None = None
    auth_type: Literal["none", "bearer", "api_key_header"] | None = None
    credentials: CredentialsRequest | None = None
    timeout_seconds: int | None = Field(default=None, gt=0, le=300)


class SetEnabledRequest(_StrictRequest):
    """Explicitly enable or disable a connection or discovered tool."""

    enabled: bool


class MCPConnectionResponse(BaseModel):
    """Safe persisted connection metadata returned to its owner."""

    id: UUID
    name: str
    transport: str
    server_url: str | None
    stdio_template_code: str | None
    configuration: dict[str, Any]
    auth_type: str
    credentials_configured: bool
    is_enabled: bool
    timeout_seconds: int
    # This is the last persisted test result, not a claim that a live client
    # currently exists in this FastAPI process.
    last_test_status: str = Field(validation_alias="status")
    last_tested_at: datetime | None
    last_error_code: str | None
    last_discovered_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MCPToolResponse(BaseModel):
    """Validated discovery metadata plus the user's approval state."""

    id: UUID
    connection_id: UUID
    remote_name: str
    public_name: str
    description: str | None
    input_schema: dict[str, Any]
    server_annotations: dict[str, Any] | None
    is_enabled: bool
    is_available: bool
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MCPRuntimeActionResponse(BaseModel):
    """Current process-local result of connecting or disconnecting."""

    connection_id: UUID
    state: Literal["connected", "disconnected", "starting", "stopping"]
    tool_count: int = 0


class MCPConnectionTestResponse(BaseModel):
    """Safe persisted result of an explicit connect-and-cleanup test."""

    success: bool
    status: str
    error_code: str | None = None
    tool_count: int = 0


class MCPDiscoveryResponse(BaseModel):
    """Tools returned after one explicit user-triggered discovery refresh."""

    connection_id: UUID
    tools: list[MCPToolResponse]


class DeleteMCPConnectionResponse(BaseModel):
    """Confirmation returned only after persistence and cleanup succeed."""

    deleted: bool
    connection_id: UUID
