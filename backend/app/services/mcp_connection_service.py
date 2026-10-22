"""Business rules for persisted, user-owned MCP connection definitions.

This service validates transport settings, encrypts credentials, exposes only
redacted connection views, and synchronizes untrusted discovery metadata with a
disabled-by-default policy. It never opens an MCP connection or launches a
process; the lifespan-owned MCP runtime handles live transport state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.mcp.security.connection_validation import (
    MCPConnectionConfigValidator,
)
from app.models.mcp_connection import MCPConnection
from app.models.mcp_connection_tool import MCPConnectionTool
from app.repositories.mcp_connection_repository import (
    MCPConnectionRepository,
)
from app.repositories.mcp_connection_tool_repository import (
    MCPConnectionToolRepository,
)
from app.services.credential_encryption_service import (
    CredentialEncryptionService,
)


SUPPORTED_AUTH_TYPES = frozenset({"none", "bearer", "api_key_header"})
ALLOWED_API_KEY_HEADERS = frozenset({"api-key", "x-api-key"})
SAFE_ERROR_CODE = re.compile(r"^[a-z0-9_.-]{1,100}$")
MAX_DISCOVERY_JSON_CHARS = 64_000
MAX_TOOL_NAME_CHARS = 255
MAX_TOOL_DESCRIPTION_CHARS = 8_000
MAX_PUBLIC_TOOL_NAME_CHARS = 64
MAX_CREDENTIAL_JSON_CHARS = 16_000
MCP_UNSET = object()


@dataclass(frozen=True, slots=True)
class MCPConnectionDetails:
    """Safe connection fields suitable for a future API response."""

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
    status: str
    last_tested_at: datetime | None
    last_error_code: str | None
    last_discovered_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DiscoveredMCPTool:
    """Untrusted tool metadata received from an MCP discovery response."""

    name: str
    description: str | None
    input_schema: Mapping[str, Any]
    annotations: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class MCPToolDetails:
    """Safe persisted tool metadata and the user's explicit trust choice."""

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


def _canonical_json(value: Any) -> str:
    """Serialize metadata consistently for hashing and bounded-size checks."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("MCP metadata must contain valid JSON values.") from exc


def _build_public_tool_name(connection_id: UUID, remote_name: str) -> str:
    """Build a stable model-safe name without using an editable display name."""
    normalized = re.sub(r"[^a-zA-Z0-9_-]", "_", remote_name).strip("_")
    normalized = normalized or "tool"
    prefix = f"mcp_{connection_id.hex[:8]}_"
    digest = hashlib.sha256(remote_name.encode("utf-8")).hexdigest()[:8]
    available = MAX_PUBLIC_TOOL_NAME_CHARS - len(prefix) - len(digest) - 1
    return f"{prefix}{normalized[:available]}_{digest}"


class MCPConnectionService:
    """Validate and persist MCP settings without starting any MCP runtime."""

    def __init__(
        self,
        db: Session,
        *,
        credential_encryption_service: CredentialEncryptionService | None = None,
        config_validator: MCPConnectionConfigValidator | None = None,
    ) -> None:
        """Create repositories and reusable security helpers for one session."""
        self.db = db
        self.connection_repository = MCPConnectionRepository(db)
        self.tool_repository = MCPConnectionToolRepository(db)
        # Keep encryption lazy so listing or synchronizing non-secret data does
        # not require the application encryption key during process startup.
        self.credential_encryption_service = credential_encryption_service
        self.config_validator = (
            config_validator or MCPConnectionConfigValidator()
        )

    def _connection_details(
        self,
        connection: MCPConnection,
    ) -> MCPConnectionDetails:
        """Create a redacted view that cannot expose stored ciphertext."""
        return MCPConnectionDetails(
            id=connection.id,
            name=connection.name,
            transport=connection.transport,
            server_url=connection.server_url,
            stdio_template_code=connection.stdio_template_code,
            configuration=deepcopy(connection.configuration),
            auth_type=connection.auth_type,
            credentials_configured=bool(connection.encrypted_credentials),
            is_enabled=connection.is_enabled,
            timeout_seconds=connection.timeout_seconds,
            status=connection.status,
            last_tested_at=connection.last_tested_at,
            last_error_code=connection.last_error_code,
            last_discovered_at=connection.last_discovered_at,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )

    def _tool_details(self, tool: MCPConnectionTool) -> MCPToolDetails:
        """Copy tool metadata into a safe immutable service result."""
        return MCPToolDetails(
            id=tool.id,
            connection_id=tool.connection_id,
            remote_name=tool.remote_name,
            public_name=tool.public_name,
            description=tool.description,
            input_schema=deepcopy(tool.input_schema),
            server_annotations=(
                deepcopy(tool.server_annotations)
                if tool.server_annotations is not None
                else None
            ),
            is_enabled=tool.is_enabled,
            is_available=tool.is_available,
            last_seen_at=tool.last_seen_at,
        )

    def _encrypt_credentials(
        self,
        *,
        transport: str,
        auth_type: str,
        credentials: Mapping[str, str] | None,
    ) -> str | None:
        """Validate a limited authentication shape and encrypt it as one value."""
        if auth_type not in SUPPORTED_AUTH_TYPES:
            raise ValueError("Unsupported MCP authentication type.")
        supplied = dict(credentials or {})

        # Phase 2 permits no user-supplied environment secrets for stdio.
        if transport == "stdio" and auth_type != "none":
            raise ValueError(
                "Stdio credentials must be supplied by an approved template."
            )

        if auth_type == "none":
            if supplied:
                raise ValueError(
                    "Credentials cannot be supplied when authentication is none."
                )
            return None

        if auth_type == "bearer":
            if set(supplied) != {"token"} or not supplied["token"].strip():
                raise ValueError("Bearer authentication requires one token.")
            supplied["token"] = supplied["token"].strip()

        if auth_type == "api_key_header":
            if set(supplied) != {"header_name", "api_key"}:
                raise ValueError(
                    "API-key authentication requires header_name and api_key."
                )
            header_name = supplied["header_name"].strip().lower()
            if header_name not in ALLOWED_API_KEY_HEADERS:
                raise ValueError("The requested API-key header is not allowed.")
            if not supplied["api_key"].strip():
                raise ValueError("API key cannot be empty.")
            supplied["header_name"] = header_name
            supplied["api_key"] = supplied["api_key"].strip()

        encoded = _canonical_json(supplied)
        if len(encoded) > MAX_CREDENTIAL_JSON_CHARS:
            raise ValueError("MCP credentials are too large.")
        if self.credential_encryption_service is None:
            self.credential_encryption_service = CredentialEncryptionService()
        return self.credential_encryption_service.encrypt(encoded)

    def create_connection(
        self,
        *,
        user_id: UUID,
        name: str,
        transport: str,
        server_url: str | None = None,
        stdio_template_code: str | None = None,
        configuration: Mapping[str, Any] | None = None,
        auth_type: str = "none",
        credentials: Mapping[str, str] | None = None,
        timeout_seconds: int = 30,
    ) -> MCPConnectionDetails:
        """Validate, encrypt, and save a disabled user-owned connection."""
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("MCP connection name cannot be empty.")
        if len(normalized_name) > 100:
            raise ValueError("MCP connection name is too long.")
        if timeout_seconds <= 0:
            raise ValueError("MCP timeout must be greater than zero.")
        if self.connection_repository.get_by_name(
            name=normalized_name,
            user_id=user_id,
        ) is not None:
            raise ValueError("An MCP connection with this name already exists.")

        validated = self.config_validator.validate(
            transport=transport,
            server_url=server_url,
            stdio_template_code=stdio_template_code,
            configuration=configuration,
        )
        encrypted_credentials = self._encrypt_credentials(
            transport=validated.transport,
            auth_type=auth_type,
            credentials=credentials,
        )
        connection = self.connection_repository.create(
            user_id=user_id,
            name=normalized_name,
            transport=validated.transport,
            server_url=validated.server_url,
            stdio_template_code=validated.stdio_template_code,
            configuration=validated.configuration,
            auth_type=auth_type,
            encrypted_credentials=encrypted_credentials,
            timeout_seconds=timeout_seconds,
        )
        return self._connection_details(connection)

    def get_connection(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
    ) -> MCPConnectionDetails:
        """Return a redacted connection only when the owner matches."""
        connection = self.connection_repository.get_by_id(
            connection_id=connection_id,
            user_id=user_id,
        )
        if connection is None:
            raise ValueError("MCP connection not found.")
        return self._connection_details(connection)

    def list_connections(self, *, user_id: UUID) -> list[MCPConnectionDetails]:
        """Return redacted connection definitions for one user only."""
        return [
            self._connection_details(connection)
            for connection in self.connection_repository.list_by_user(
                user_id=user_id
            )
        ]

    def update_connection(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
        updates: Mapping[str, Any],
    ) -> MCPConnectionDetails:
        """Validate and update editable fields without exposing credentials."""
        allowed_fields = {
            "name",
            "transport",
            "server_url",
            "stdio_template_code",
            "configuration",
            "auth_type",
            "credentials",
            "timeout_seconds",
        }
        if set(updates) - allowed_fields:
            raise ValueError("Unsupported MCP connection update field.")
        connection = self.connection_repository.get_by_id(
            connection_id=connection_id,
            user_id=user_id,
        )
        if connection is None:
            raise ValueError("MCP connection not found.")

        name = updates.get("name", connection.name)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("MCP connection name cannot be empty.")
        name = name.strip()
        if len(name) > 100:
            raise ValueError("MCP connection name is too long.")
        named = self.connection_repository.get_by_name(
            name=name,
            user_id=user_id,
        )
        if named is not None and named.id != connection_id:
            raise ValueError("An MCP connection with this name already exists.")

        timeout_seconds = updates.get(
            "timeout_seconds",
            connection.timeout_seconds,
        )
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError("MCP timeout must be greater than zero.")

        validated = self.config_validator.validate(
            transport=updates.get("transport", connection.transport),
            server_url=updates.get("server_url", connection.server_url),
            stdio_template_code=updates.get(
                "stdio_template_code",
                connection.stdio_template_code,
            ),
            configuration=updates.get(
                "configuration",
                connection.configuration,
            ),
        )
        auth_type = updates.get("auth_type", connection.auth_type)
        if auth_type not in SUPPORTED_AUTH_TYPES:
            raise ValueError("Unsupported MCP authentication type.")

        credentials = updates.get("credentials", MCP_UNSET)
        if credentials is MCP_UNSET:
            if auth_type == "none":
                encrypted_credentials = None
            elif auth_type != connection.auth_type:
                raise ValueError(
                    "New credentials are required when authentication changes."
                )
            else:
                encrypted_credentials = connection.encrypted_credentials
                if encrypted_credentials is None:
                    raise ValueError("MCP credentials are required.")
            if validated.transport == "stdio" and auth_type != "none":
                raise ValueError(
                    "Stdio credentials must be supplied by an approved template."
                )
        else:
            encrypted_credentials = self._encrypt_credentials(
                transport=validated.transport,
                auth_type=auth_type,
                credentials=credentials,
            )

        values = {
            "name": name,
            "transport": validated.transport,
            "server_url": validated.server_url,
            "stdio_template_code": validated.stdio_template_code,
            "configuration": validated.configuration,
            "auth_type": auth_type,
            "encrypted_credentials": encrypted_credentials,
            "timeout_seconds": timeout_seconds,
        }
        runtime_fields = {
            "transport",
            "server_url",
            "stdio_template_code",
            "configuration",
            "auth_type",
            "credentials",
            "timeout_seconds",
        }
        runtime_changed = any(field in updates for field in runtime_fields)
        trust_fields = runtime_fields - {"timeout_seconds"}
        trust_changed = any(field in updates for field in trust_fields)
        if runtime_changed:
            values.update(
                {
                    "status": "not_tested",
                    "last_tested_at": None,
                    "last_error_code": None,
                }
            )
        if trust_changed:
            values["last_discovered_at"] = None
            self.tool_repository.disable_all(
                connection_id=connection_id,
                user_id=user_id,
                mark_unavailable=True,
            )

        updated = self.connection_repository.update(
            connection_id=connection_id,
            user_id=user_id,
            values=values,
        )
        if updated is None:
            raise ValueError("MCP connection not found.")
        return self._connection_details(updated)

    def set_connection_enabled(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
        enabled: bool,
    ) -> MCPConnectionDetails:
        """Persist whether this owned connection may start or execute tools."""
        connection = self.connection_repository.set_enabled(
            connection_id=connection_id,
            user_id=user_id,
            enabled=enabled,
        )
        if connection is None:
            raise ValueError("MCP connection not found.")
        return self._connection_details(connection)

    def delete_connection(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
    ) -> None:
        """Delete one owned persisted definition and its discovered tools."""
        if not self.connection_repository.delete(
            connection_id=connection_id,
            user_id=user_id,
        ):
            raise ValueError("MCP connection not found.")

    def record_test_result(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
        success: bool,
        error_code: str | None = None,
        tested_at: datetime | None = None,
    ) -> MCPConnectionDetails:
        """Persist readiness using a stable safe code, never a raw exception."""
        if success:
            error_code = None
        elif error_code is None or SAFE_ERROR_CODE.fullmatch(error_code) is None:
            raise ValueError("A safe MCP error code is required for failure.")

        connection = self.connection_repository.record_test_result(
            connection_id=connection_id,
            user_id=user_id,
            status="ready" if success else "error",
            tested_at=tested_at or datetime.now(timezone.utc),
            error_code=error_code,
        )
        if connection is None:
            raise ValueError("MCP connection not found.")
        return self._connection_details(connection)

    def synchronize_discovered_tools(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
        discovered_tools: Iterable[DiscoveredMCPTool],
        discovered_at: datetime | None = None,
    ) -> list[MCPToolDetails]:
        """Persist untrusted discovery metadata with trust disabled by default."""
        if self.connection_repository.get_by_id(
            connection_id=connection_id,
            user_id=user_id,
        ) is None:
            raise ValueError("MCP connection not found.")

        prepared: list[dict[str, Any]] = []
        names: set[str] = set()
        for discovered in discovered_tools:
            remote_name = discovered.name.strip()
            if not remote_name or len(remote_name) > MAX_TOOL_NAME_CHARS:
                raise ValueError("MCP tool name is missing or too long.")
            if remote_name in names:
                raise ValueError("MCP discovery returned duplicate tool names.")
            names.add(remote_name)

            if discovered.description is not None and len(
                discovered.description
            ) > MAX_TOOL_DESCRIPTION_CHARS:
                raise ValueError("MCP tool description is too long.")

            input_schema = dict(discovered.input_schema)
            if input_schema.get("type") not in (None, "object"):
                raise ValueError("MCP tool input schema must describe an object.")
            annotations = (
                dict(discovered.annotations)
                if discovered.annotations is not None
                else None
            )
            encoded_schema = _canonical_json(input_schema)
            encoded_annotations = _canonical_json(annotations)
            if (
                len(encoded_schema) > MAX_DISCOVERY_JSON_CHARS
                or len(encoded_annotations) > MAX_DISCOVERY_JSON_CHARS
            ):
                raise ValueError("MCP tool metadata is too large.")

            prepared.append(
                {
                    "remote_name": remote_name,
                    "public_name": _build_public_tool_name(
                        connection_id,
                        remote_name,
                    ),
                    "description": discovered.description,
                    "input_schema": input_schema,
                    "schema_hash": hashlib.sha256(
                        encoded_schema.encode("utf-8")
                    ).hexdigest(),
                    # Advisory data is stored but never read as authorization.
                    "server_annotations": annotations,
                }
            )

        timestamp = discovered_at or datetime.now(timezone.utc)
        synchronized = self.tool_repository.synchronize_discovered(
            connection_id=connection_id,
            user_id=user_id,
            discovered_tools=prepared,
            discovered_at=timestamp,
        )
        self.connection_repository.record_discovery(
            connection_id=connection_id,
            user_id=user_id,
            discovered_at=timestamp,
        )
        return [self._tool_details(tool) for tool in synchronized]

    def list_tools(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
    ) -> list[MCPToolDetails]:
        """Return tool metadata only through an owned parent connection."""
        if self.connection_repository.get_by_id(
            connection_id=connection_id,
            user_id=user_id,
        ) is None:
            raise ValueError("MCP connection not found.")
        return [
            self._tool_details(tool)
            for tool in self.tool_repository.list_by_connection(
                connection_id=connection_id,
                user_id=user_id,
            )
        ]

    def get_tool(
        self,
        *,
        connection_id: UUID,
        tool_id: UUID,
        user_id: UUID,
    ) -> MCPToolDetails:
        """Return one tool only through its owned parent connection."""
        tool = self.tool_repository.get_by_id(
            tool_id=tool_id,
            connection_id=connection_id,
            user_id=user_id,
        )
        if tool is None:
            raise ValueError("MCP tool not found.")
        return self._tool_details(tool)

    def set_tool_enabled(
        self,
        *,
        connection_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        enabled: bool,
    ) -> MCPToolDetails:
        """Persist explicit trust after checking tool, connection, and owner."""
        tool = self.tool_repository.set_enabled(
            tool_id=tool_id,
            connection_id=connection_id,
            user_id=user_id,
            enabled=enabled,
        )
        if tool is None:
            raise ValueError("MCP tool not found.")
        return self._tool_details(tool)
