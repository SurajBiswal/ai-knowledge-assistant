"""Test MCP models, ownership, encryption, and discovery trust policies."""

from __future__ import annotations

from dataclasses import asdict
import json
import sys

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.mcp.config.stdio_templates import ApprovedStdioServerTemplate
from app.mcp.security.connection_validation import (
    MCPConnectionConfigValidator,
)
from app.models.mcp_connection import MCPConnection
from app.models.mcp_connection_tool import MCPConnectionTool
from app.models.user import User
from app.services.credential_encryption_service import (
    CredentialEncryptionService,
)
from app.services.mcp_connection_service import (
    DiscoveredMCPTool,
    MCPConnectionService,
)


@pytest.fixture
def db() -> Session:
    """Create only the Phase 2 tables in an isolated in-memory database."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite needs this switch to enforce the same cascade foreign keys used by
    # PostgreSQL in the production migration.
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            MCPConnection.__table__,
            MCPConnectionTool.__table__,
        ],
    )
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(
            engine,
            tables=[
                MCPConnectionTool.__table__,
                MCPConnection.__table__,
                User.__table__,
            ],
        )
        engine.dispose()


@pytest.fixture
def users(db: Session) -> tuple[User, User]:
    """Create two owners so every repository test can prove isolation."""
    user_a = User(
        name="User A",
        email="user-a@example.test",
        password_hash="hash-a",
    )
    user_b = User(
        name="User B",
        email="user-b@example.test",
        password_hash="hash-b",
    )
    db.add_all([user_a, user_b])
    db.flush()
    return user_a, user_b


@pytest.fixture
def encryption_service() -> CredentialEncryptionService:
    """Use a test-only Fernet key that never enters application configuration."""
    return CredentialEncryptionService(Fernet.generate_key().decode())


@pytest.fixture
def service(
    db: Session,
    encryption_service: CredentialEncryptionService,
) -> MCPConnectionService:
    """Build the service with one approved template and deterministic DNS."""
    template = ApprovedStdioServerTemplate(
        code="safe_echo",
        name="Safe Echo",
        command=sys.executable,
        allowed_configuration_keys=frozenset({"workspace"}),
    )
    validator = MCPConnectionConfigValidator(
        stdio_templates={template.code: template},
        host_resolver=lambda _hostname: {"8.8.8.8"},
    )
    return MCPConnectionService(
        db,
        credential_encryption_service=encryption_service,
        config_validator=validator,
    )


def create_stdio_connection(
    service: MCPConnectionService,
    *,
    user: User,
    name: str = "Local Workspace",
):
    """Save one approved connection for model and ownership tests."""
    return service.create_connection(
        user_id=user.id,
        name=name,
        transport="stdio",
        stdio_template_code="safe_echo",
        configuration={"workspace": user.name},
    )


def test_models_link_user_connection_and_discovered_tools(
    db: Session,
    users: tuple[User, User],
    service: MCPConnectionService,
) -> None:
    """Verify both ORM relationships and safe database cascade ownership."""
    user_a, _ = users
    connection = create_stdio_connection(service, user=user_a)
    tools = service.synchronize_discovered_tools(
        connection_id=connection.id,
        user_id=user_a.id,
        discovered_tools=[
            DiscoveredMCPTool(
                name="echo",
                description="Echo text.",
                input_schema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                },
            )
        ],
    )

    db.expire_all()
    stored_user = db.get(User, user_a.id)
    stored_connection = service.connection_repository.get_by_id(
        connection_id=connection.id,
        user_id=user_a.id,
    )

    assert stored_user is not None
    assert [item.id for item in stored_user.mcp_connections] == [connection.id]
    assert stored_connection is not None
    assert [tool.id for tool in stored_connection.tools] == [tools[0].id]
    assert stored_connection.tools[0].connection is stored_connection


def test_repositories_enforce_connection_and_tool_ownership(
    users: tuple[User, User],
    service: MCPConnectionService,
) -> None:
    """Ensure User B cannot access User A's connection or discovered tool."""
    user_a, user_b = users
    connection = create_stdio_connection(service, user=user_a)
    tool = service.synchronize_discovered_tools(
        connection_id=connection.id,
        user_id=user_a.id,
        discovered_tools=[
            DiscoveredMCPTool(
                name="echo",
                description=None,
                input_schema={"type": "object"},
            )
        ],
    )[0]

    assert service.connection_repository.get_by_id(
        connection_id=connection.id,
        user_id=user_b.id,
    ) is None
    assert service.tool_repository.get_by_id(
        tool_id=tool.id,
        connection_id=connection.id,
        user_id=user_b.id,
    ) is None

    with pytest.raises(ValueError, match="connection not found"):
        service.get_connection(
            connection_id=connection.id,
            user_id=user_b.id,
        )
    with pytest.raises(ValueError, match="tool not found"):
        service.set_tool_enabled(
            connection_id=connection.id,
            tool_id=tool.id,
            user_id=user_b.id,
            enabled=True,
        )


def test_discovered_tools_start_disabled_and_annotations_are_advisory(
    users: tuple[User, User],
    service: MCPConnectionService,
) -> None:
    """Keep server claims from granting trust and revoke trust on schema change."""
    user_a, _ = users
    connection = create_stdio_connection(service, user=user_a)
    original = DiscoveredMCPTool(
        name="read_file",
        description="Read a file.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
        annotations={"readOnlyHint": True},
    )

    discovered = service.synchronize_discovered_tools(
        connection_id=connection.id,
        user_id=user_a.id,
        discovered_tools=[original],
    )[0]
    assert discovered.is_enabled is False
    assert discovered.server_annotations == {"readOnlyHint": True}

    enabled = service.set_tool_enabled(
        connection_id=connection.id,
        tool_id=discovered.id,
        user_id=user_a.id,
        enabled=True,
    )
    assert enabled.is_enabled is True

    unchanged = service.synchronize_discovered_tools(
        connection_id=connection.id,
        user_id=user_a.id,
        discovered_tools=[original],
    )[0]
    assert unchanged.is_enabled is True

    changed = service.synchronize_discovered_tools(
        connection_id=connection.id,
        user_id=user_a.id,
        discovered_tools=[
            DiscoveredMCPTool(
                name="read_file",
                description="Read a file with extra options.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "encoding": {"type": "string"},
                    },
                },
                annotations={"readOnlyHint": True},
            )
        ],
    )[0]
    assert changed.id == discovered.id
    assert changed.is_enabled is False


def test_removed_tool_becomes_unavailable_and_disabled(
    users: tuple[User, User],
    service: MCPConnectionService,
) -> None:
    """Ensure disappearance during discovery removes earlier explicit trust."""
    user_a, _ = users
    connection = create_stdio_connection(service, user=user_a)
    tool = service.synchronize_discovered_tools(
        connection_id=connection.id,
        user_id=user_a.id,
        discovered_tools=[
            DiscoveredMCPTool(
                name="temporary_tool",
                description=None,
                input_schema={"type": "object"},
            )
        ],
    )[0]
    service.set_tool_enabled(
        connection_id=connection.id,
        tool_id=tool.id,
        user_id=user_a.id,
        enabled=True,
    )

    service.synchronize_discovered_tools(
        connection_id=connection.id,
        user_id=user_a.id,
        discovered_tools=[],
    )
    stored = service.list_tools(
        connection_id=connection.id,
        user_id=user_a.id,
    )[0]

    assert stored.is_available is False
    assert stored.is_enabled is False


def test_credentials_are_encrypted_and_redacted_from_service_results(
    users: tuple[User, User],
    service: MCPConnectionService,
    encryption_service: CredentialEncryptionService,
) -> None:
    """Store bearer data only as ciphertext and return a configured flag."""
    user_a, _ = users
    plaintext_token = "phase-two-secret-token"
    details = service.create_connection(
        user_id=user_a.id,
        name="Remote MCP",
        transport="streamable_http",
        server_url="https://mcp.example.com/mcp",
        auth_type="bearer",
        credentials={"token": plaintext_token},
    )
    stored = service.connection_repository.get_by_id(
        connection_id=details.id,
        user_id=user_a.id,
    )

    assert stored is not None
    assert stored.encrypted_credentials is not None
    assert plaintext_token not in stored.encrypted_credentials
    assert json.loads(
        encryption_service.decrypt(stored.encrypted_credentials)
    ) == {"token": plaintext_token}

    safe_result = asdict(details)
    assert details.credentials_configured is True
    assert "encrypted_credentials" not in safe_result
    assert plaintext_token not in repr(details)


def test_api_key_auth_rejects_unapproved_header_names(
    users: tuple[User, User],
    service: MCPConnectionService,
) -> None:
    """Prevent generic credentials from becoming arbitrary outbound headers."""
    user_a, _ = users

    with pytest.raises(ValueError, match="header is not allowed"):
        service.create_connection(
            user_id=user_a.id,
            name="Unsafe Header",
            transport="streamable_http",
            server_url="https://mcp.example.com/mcp",
            auth_type="api_key_header",
            credentials={
                "header_name": "Host",
                "api_key": "secret-value",
            },
        )


def test_connection_status_persists_only_safe_error_codes(
    users: tuple[User, User],
    service: MCPConnectionService,
) -> None:
    """Reject raw diagnostic text that could accidentally contain a secret."""
    user_a, _ = users
    connection = create_stdio_connection(service, user=user_a)

    with pytest.raises(ValueError, match="safe MCP error code"):
        service.record_test_result(
            connection_id=connection.id,
            user_id=user_a.id,
            success=False,
            error_code="failed with token=secret value",
        )

    recorded = service.record_test_result(
        connection_id=connection.id,
        user_id=user_a.id,
        success=False,
        error_code="connection_timeout",
    )
    assert recorded.status == "error"
    assert recorded.last_error_code == "connection_timeout"
    assert recorded.last_tested_at is not None
