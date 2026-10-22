"""Test authenticated MCP management routes without opening real transports.

The API tests use the production service, repositories, schemas, and router.
A controllable runtime double implements the real async runtime interface;
real stdio lifecycle behavior remains covered by the existing integration tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.api.error_handlers import safe_validation_exception_handler
from app.api.mcp.router import (
    get_mcp_connection_service,
    get_mcp_runtime,
    router,
)
from app.core.dependencies import get_current_user
from app.database.base import Base
from app.database.session import get_db
from app.mcp.config.stdio_templates import ApprovedStdioServerTemplate
from app.mcp.runtime import MCPRuntimeError, MCPRuntimeStatus
from app.mcp.security.connection_validation import MCPConnectionConfigValidator
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


ECHO_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
}
CHANGED_ECHO_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "uppercase": {"type": "boolean"},
    },
}


class FakeManagementRuntime:
    """Provide deterministic responses through the production runtime interface."""

    def __init__(
        self,
        *,
        SessionFactory,
        encryption: CredentialEncryptionService,
        validator: MCPConnectionConfigValidator,
    ) -> None:
        """Store test persistence helpers and start with no simulated failures."""
        self.SessionFactory = SessionFactory
        self.encryption = encryption
        self.validator = validator
        self.calls: list[tuple[str, UUID, UUID]] = []
        self.discovery: list[DiscoveredMCPTool] = [
            DiscoveredMCPTool(
                name="echo",
                description="Echo text.",
                input_schema=ECHO_SCHEMA,
            )
        ]
        self.fail_invalidation = False
        self.remote_http_egress_protected = False
        self.owner_tasks: set[Any] = set()

    def _owned_connection(self, user_id: UUID, connection_id: UUID):
        """Load current persisted state exactly when a runtime action starts."""
        with self.SessionFactory() as db:
            connection = db.query(MCPConnection).filter_by(
                id=connection_id,
                user_id=user_id,
            ).one_or_none()
            if connection is None:
                raise MCPRuntimeError(
                    "connection_not_found",
                    "MCP connection not found.",
                )
            return {
                "enabled": connection.is_enabled,
                "transport": connection.transport,
                "name": connection.name,
            }

    def _check_connectable(self, user_id: UUID, connection_id: UUID):
        """Mirror enabled-state and remote-HTTP gates used by MCPRuntime."""
        connection = self._owned_connection(user_id, connection_id)
        if not connection["enabled"]:
            raise MCPRuntimeError(
                "connection_disabled",
                "MCP connection is disabled.",
            )
        if (
            connection["transport"] == "streamable_http"
            and not self.remote_http_egress_protected
        ):
            raise MCPRuntimeError(
                "remote_http_disabled",
                "Remote MCP HTTP connections are disabled by deployment policy.",
            )
        return connection

    async def connect(self, *, user_id: UUID, connection_id: UUID):
        """Record an explicit connect after enforcing current persisted state."""
        self._check_connectable(user_id, connection_id)
        self.calls.append(("connect", user_id, connection_id))
        return MCPRuntimeStatus(
            user_id=user_id,
            connection_id=connection_id,
            state="connected",
            tool_count=len(self.discovery),
        )

    async def disconnect(self, *, user_id: UUID, connection_id: UUID):
        """Record an explicit disconnect without requiring enablement."""
        self._owned_connection(user_id, connection_id)
        self.calls.append(("disconnect", user_id, connection_id))
        return MCPRuntimeStatus(
            user_id=user_id,
            connection_id=connection_id,
            state="disconnected",
        )

    async def invalidate_connection(
        self,
        *,
        user_id: UUID,
        connection_id: UUID,
    ):
        """Observe committed data and optionally simulate incomplete cleanup."""
        self._owned_connection(user_id, connection_id)
        self.calls.append(("invalidate", user_id, connection_id))
        if self.fail_invalidation:
            raise MCPRuntimeError(
                "disconnect_incomplete",
                "The MCP connection is still stopping.",
            )
        return MCPRuntimeStatus(
            user_id=user_id,
            connection_id=connection_id,
            state="disconnected",
        )

    async def refresh_tools(self, *, user_id: UUID, connection_id: UUID):
        """Persist controlled discovery exactly as the production runtime does."""
        self._check_connectable(user_id, connection_id)
        self.calls.append(("refresh", user_id, connection_id))
        with self.SessionFactory() as db:
            service = MCPConnectionService(
                db,
                credential_encryption_service=self.encryption,
                config_validator=self.validator,
            )
            tools = service.synchronize_discovered_tools(
                user_id=user_id,
                connection_id=connection_id,
                discovered_tools=self.discovery,
            )
            db.commit()
            return tools


@pytest.fixture
def api_environment(tmp_path: Path):
    """Build an isolated API, database, users, service, and runtime double."""
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'mcp_api.db'}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_wal(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            MCPConnection.__table__,
            MCPConnectionTool.__table__,
        ],
    )
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)
    encryption = CredentialEncryptionService(Fernet.generate_key().decode())
    template = ApprovedStdioServerTemplate(
        code="api_echo",
        name="API Echo",
        command="/approved/api-echo",
    )
    validator = MCPConnectionConfigValidator(
        stdio_templates={template.code: template},
        host_resolver=lambda _hostname: {"8.8.8.8"},
    )
    with SessionFactory() as db:
        user_a = User(
            name="User A",
            email="user-a@example.test",
            password_hash="test-hash",
        )
        user_b = User(
            name="User B",
            email="user-b@example.test",
            password_hash="test-hash",
        )
        db.add_all([user_a, user_b])
        db.commit()

    runtime = FakeManagementRuntime(
        SessionFactory=SessionFactory,
        encryption=encryption,
        validator=validator,
    )
    application = FastAPI()
    application.add_exception_handler(
        RequestValidationError,
        safe_validation_exception_handler,
    )
    application.include_router(router)

    def override_db() -> Iterator[Session]:
        db = SessionFactory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def override_current_user(
        authorization: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> User:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            user_id = UUID(authorization.removeprefix("Bearer "))
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid token") from None
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def override_service(
        db: Session = Depends(get_db),
    ) -> MCPConnectionService:
        return MCPConnectionService(
            db,
            credential_encryption_service=encryption,
            config_validator=validator,
        )

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_current_user] = override_current_user
    application.dependency_overrides[get_mcp_connection_service] = (
        override_service
    )
    application.dependency_overrides[get_mcp_runtime] = lambda: runtime

    client = TestClient(application)
    environment = {
        "client": client,
        "SessionFactory": SessionFactory,
        "encryption": encryption,
        "validator": validator,
        "runtime": runtime,
        "user_a": user_a,
        "user_b": user_b,
    }
    try:
        yield environment
    finally:
        client.close()
        Base.metadata.drop_all(
            engine,
            tables=[
                MCPConnectionTool.__table__,
                MCPConnection.__table__,
                User.__table__,
            ],
        )
        engine.dispose()


def auth(user: User) -> dict[str, str]:
    """Encode the test user's UUID as the overridden bearer identity."""
    return {"Authorization": f"Bearer {user.id}"}


def create_stdio_connection(environment, *, user: User, name: str = "Echo"):
    """Create one disabled stdio connection through the public API."""
    response = environment["client"].post(
        "/api/mcp/connections",
        headers=auth(user),
        json={
            "name": name,
            "transport": "stdio",
            "stdio_template_code": "api_echo",
            "configuration": {},
            "auth_type": "none",
            "timeout_seconds": 30,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def set_connection_enabled(environment, *, user: User, connection_id, enabled=True):
    """Change connection availability through the public endpoint."""
    response = environment["client"].patch(
        f"/api/mcp/connections/{connection_id}/enabled",
        headers=auth(user),
        json={"enabled": enabled},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_unauthenticated_requests_are_rejected(api_environment) -> None:
    """Require authentication even for connection listing."""
    response = api_environment["client"].get("/api/mcp/connections")
    assert response.status_code == 401


def test_credentials_are_encrypted_redacted_and_validation_is_secret_safe(
    api_environment,
    caplog,
) -> None:
    """Never persist plaintext or echo submitted secrets in responses or logs."""
    client = api_environment["client"]
    user = api_environment["user_a"]
    secret = "phase-four-super-secret"
    response = client.post(
        "/api/mcp/connections",
        headers=auth(user),
        json={
            "name": "Remote",
            "transport": "streamable_http",
            "server_url": "https://mcp.example.test/mcp",
            "auth_type": "bearer",
            "credentials": {"token": secret},
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["credentials_configured"] is True
    assert body["last_test_status"] == "not_tested"
    assert "status" not in body
    assert secret not in response.text
    assert "encrypted_credentials" not in body

    with api_environment["SessionFactory"]() as db:
        stored = db.get(MCPConnection, UUID(body["id"]))
        assert stored is not None
        assert stored.encrypted_credentials is not None
        assert stored.encrypted_credentials != secret
        plaintext = api_environment["encryption"].decrypt(
            stored.encrypted_credentials
        )
        assert secret in plaintext

    invalid = client.post(
        "/api/mcp/connections",
        headers=auth(user),
        json={
            "name": "Unknown field",
            "transport": "stdio",
            "stdio_template_code": "api_echo",
            "credentials": None,
            "unexpected_secret": secret,
        },
    )
    assert invalid.status_code == 422
    assert secret not in invalid.text
    assert secret not in caplog.text

    invalid_url = client.post(
        "/api/mcp/connections",
        headers=auth(user),
        json={
            "name": "Private",
            "transport": "streamable_http",
            "server_url": "https://127.0.0.1/mcp",
        },
    )
    assert invalid_url.status_code == 400


def test_request_user_id_cannot_override_authenticated_owner(
    api_environment,
) -> None:
    """Reject user_id rather than trusting it as connection ownership."""
    response = api_environment["client"].post(
        "/api/mcp/connections",
        headers=auth(api_environment["user_a"]),
        json={
            "name": "Forged",
            "transport": "stdio",
            "stdio_template_code": "api_echo",
            "user_id": str(api_environment["user_b"].id),
        },
    )
    assert response.status_code == 422
    listed = api_environment["client"].get(
        "/api/mcp/connections",
        headers=auth(api_environment["user_a"]),
    )
    assert listed.json() == []


def test_other_user_cannot_manage_connection_or_tool(api_environment) -> None:
    """Return not-found for every cross-tenant connection and tool operation."""
    owner = api_environment["user_b"]
    attacker = api_environment["user_a"]
    connection = create_stdio_connection(
        api_environment,
        user=owner,
        name="Owned by B",
    )
    set_connection_enabled(
        api_environment,
        user=owner,
        connection_id=connection["id"],
    )
    refreshed = api_environment["client"].post(
        f"/api/mcp/connections/{connection['id']}/refresh-tools",
        headers=auth(owner),
    )
    assert refreshed.status_code == 200
    tool_id = refreshed.json()["tools"][0]["id"]

    requests = [
        ("get", f"/api/mcp/connections/{connection['id']}", None),
        ("patch", f"/api/mcp/connections/{connection['id']}", {"name": "X"}),
        ("delete", f"/api/mcp/connections/{connection['id']}", None),
        ("post", f"/api/mcp/connections/{connection['id']}/test", None),
        ("post", f"/api/mcp/connections/{connection['id']}/connect", None),
        ("post", f"/api/mcp/connections/{connection['id']}/disconnect", None),
        ("post", f"/api/mcp/connections/{connection['id']}/refresh-tools", None),
        ("patch", f"/api/mcp/connections/{connection['id']}/enabled", {"enabled": False}),
        ("get", f"/api/mcp/connections/{connection['id']}/tools", None),
        ("get", f"/api/mcp/connections/{connection['id']}/tools/{tool_id}", None),
        ("patch", f"/api/mcp/connections/{connection['id']}/tools/{tool_id}/enabled", {"enabled": True}),
    ]
    calls_before = list(api_environment["runtime"].calls)
    for method, path, payload in requests:
        response = api_environment["client"].request(
            method,
            path,
            headers=auth(attacker),
            json=payload,
        )
        assert response.status_code == 404, (method, path, response.text)
    assert api_environment["runtime"].calls == calls_before


def test_update_commits_before_invalidation_and_reports_cleanup_failure(
    api_environment,
) -> None:
    """Persist safe state but return conflict when the previous owner survives."""
    user = api_environment["user_a"]
    connection = create_stdio_connection(api_environment, user=user)
    runtime = api_environment["runtime"]

    updated = api_environment["client"].patch(
        f"/api/mcp/connections/{connection['id']}",
        headers=auth(user),
        json={"name": "Committed before invalidation"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Committed before invalidation"
    assert runtime.calls[-1][0] == "invalidate"

    runtime.fail_invalidation = True
    failed = api_environment["client"].patch(
        f"/api/mcp/connections/{connection['id']}",
        headers=auth(user),
        json={"timeout_seconds": 45},
    )
    assert failed.status_code == 409
    assert failed.json()["detail"]["code"] == "disconnect_incomplete"
    with api_environment["SessionFactory"]() as db:
        stored = db.get(MCPConnection, UUID(connection["id"]))
        assert stored is not None
        assert stored.timeout_seconds == 45
        assert stored.status == "not_tested"


def test_credential_update_revokes_tools_and_invalidates_runtime(
    api_environment,
) -> None:
    """Commit a replacement secret, revoke approvals, then close old state."""
    client = api_environment["client"]
    user = api_environment["user_a"]
    runtime = api_environment["runtime"]
    runtime.remote_http_egress_protected = True
    created = client.post(
        "/api/mcp/connections",
        headers=auth(user),
        json={
            "name": "Credential update",
            "transport": "streamable_http",
            "server_url": "https://mcp.example.test/mcp",
            "auth_type": "bearer",
            "credentials": {"token": "old-private-token"},
        },
    )
    assert created.status_code == 201
    connection = created.json()
    set_connection_enabled(
        api_environment,
        user=user,
        connection_id=connection["id"],
    )
    refreshed = client.post(
        f"/api/mcp/connections/{connection['id']}/refresh-tools",
        headers=auth(user),
    )
    tool = refreshed.json()["tools"][0]
    approved = client.patch(
        f"/api/mcp/connections/{connection['id']}/tools/{tool['id']}/enabled",
        headers=auth(user),
        json={"enabled": True},
    )
    assert approved.status_code == 200

    replacement = "new-private-token"
    updated = client.patch(
        f"/api/mcp/connections/{connection['id']}",
        headers=auth(user),
        json={"credentials": {"token": replacement}},
    )
    assert updated.status_code == 200, updated.text
    assert replacement not in updated.text
    assert runtime.calls[-1][0] == "invalidate"

    persisted_tool = client.get(
        f"/api/mcp/connections/{connection['id']}/tools/{tool['id']}",
        headers=auth(user),
    ).json()
    assert persisted_tool["is_enabled"] is False
    assert persisted_tool["is_available"] is False
    with api_environment["SessionFactory"]() as db:
        stored = db.get(MCPConnection, UUID(connection["id"]))
        assert stored is not None
        assert stored.encrypted_credentials is not None
        plaintext = api_environment["encryption"].decrypt(
            stored.encrypted_credentials
        )
        assert replacement in plaintext
        assert "old-private-token" not in plaintext


def test_tool_refresh_approval_schema_change_and_removal(api_environment) -> None:
    """Keep new tools disabled and revoke approval on change or disappearance."""
    user = api_environment["user_a"]
    connection = create_stdio_connection(api_environment, user=user)
    set_connection_enabled(
        api_environment,
        user=user,
        connection_id=connection["id"],
    )
    client = api_environment["client"]
    runtime = api_environment["runtime"]
    refresh_url = f"/api/mcp/connections/{connection['id']}/refresh-tools"

    first = client.post(refresh_url, headers=auth(user))
    assert first.status_code == 200, first.text
    tool = first.json()["tools"][0]
    assert tool["is_enabled"] is False
    assert tool["is_available"] is True

    enabled = client.patch(
        f"/api/mcp/connections/{connection['id']}/tools/{tool['id']}/enabled",
        headers=auth(user),
        json={"enabled": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["is_enabled"] is True

    disabled = client.patch(
        f"/api/mcp/connections/{connection['id']}/tools/{tool['id']}/enabled",
        headers=auth(user),
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_enabled"] is False

    reenabled = client.patch(
        f"/api/mcp/connections/{connection['id']}/tools/{tool['id']}/enabled",
        headers=auth(user),
        json={"enabled": True},
    )
    assert reenabled.status_code == 200
    assert reenabled.json()["is_enabled"] is True

    same = client.post(refresh_url, headers=auth(user))
    assert same.json()["tools"][0]["is_enabled"] is True

    runtime.discovery = [
        DiscoveredMCPTool(
            name="echo",
            description="Echo text.",
            input_schema=CHANGED_ECHO_SCHEMA,
        )
    ]
    changed = client.post(refresh_url, headers=auth(user))
    assert changed.status_code == 200
    assert changed.json()["tools"][0]["is_enabled"] is False

    client.patch(
        f"/api/mcp/connections/{connection['id']}/tools/{tool['id']}/enabled",
        headers=auth(user),
        json={"enabled": True},
    )
    runtime.discovery = []
    removed = client.post(refresh_url, headers=auth(user))
    assert removed.status_code == 200
    assert removed.json()["tools"] == []
    persisted = client.get(
        f"/api/mcp/connections/{connection['id']}/tools/{tool['id']}",
        headers=auth(user),
    )
    assert persisted.status_code == 200
    assert persisted.json()["is_available"] is False
    assert persisted.json()["is_enabled"] is False


def test_owned_test_connect_and_disconnect_use_runtime(api_environment) -> None:
    """Exercise every explicit lifecycle action through the runtime contract."""
    user = api_environment["user_a"]
    connection = create_stdio_connection(api_environment, user=user)
    set_connection_enabled(
        api_environment,
        user=user,
        connection_id=connection["id"],
    )
    client = api_environment["client"]
    base_url = f"/api/mcp/connections/{connection['id']}"

    tested = client.post(f"{base_url}/test", headers=auth(user))
    assert tested.status_code == 200
    assert tested.json() == {
        "success": True,
        "status": "ready",
        "error_code": None,
        "tool_count": 1,
    }

    connected = client.post(f"{base_url}/connect", headers=auth(user))
    assert connected.status_code == 200
    assert connected.json()["state"] == "connected"

    disconnected = client.post(f"{base_url}/disconnect", headers=auth(user))
    assert disconnected.status_code == 200
    assert disconnected.json()["state"] == "disconnected"

    action_names = [call[0] for call in api_environment["runtime"].calls]
    assert action_names[-4:] == [
        "connect",
        "disconnect",
        "connect",
        "disconnect",
    ]


def test_disabled_connection_and_remote_http_gate_fail_closed(
    api_environment,
) -> None:
    """Reject disabled stdio and every remote operation while egress is unverified."""
    client = api_environment["client"]
    user = api_environment["user_a"]
    disabled = create_stdio_connection(api_environment, user=user)
    for action in ("test", "connect", "refresh-tools"):
        blocked = client.post(
            f"/api/mcp/connections/{disabled['id']}/{action}",
            headers=auth(user),
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["code"] == "connection_disabled"

    remote = client.post(
        "/api/mcp/connections",
        headers=auth(user),
        json={
            "name": "Remote gate",
            "transport": "streamable_http",
            "server_url": "https://mcp.example.test/mcp",
        },
    ).json()
    set_connection_enabled(
        api_environment,
        user=user,
        connection_id=remote["id"],
    )
    for action in ("test", "connect", "refresh-tools"):
        response = client.post(
            f"/api/mcp/connections/{remote['id']}/{action}",
            headers=auth(user),
            json={"remote_http_egress_protected": True},
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "remote_http_disabled"
    stored_remote = client.get(
        f"/api/mcp/connections/{remote['id']}",
        headers=auth(user),
    ).json()
    assert stored_remote["last_test_status"] == "error"
    assert stored_remote["last_error_code"] == "remote_http_disabled"


def test_delete_disables_before_cleanup_and_retries_honestly(
    api_environment,
) -> None:
    """Leave a failed deletion disabled, then delete it after cleanup succeeds."""
    user = api_environment["user_a"]
    connection = create_stdio_connection(api_environment, user=user)
    set_connection_enabled(
        api_environment,
        user=user,
        connection_id=connection["id"],
    )
    runtime = api_environment["runtime"]
    runtime.fail_invalidation = True
    failed = api_environment["client"].delete(
        f"/api/mcp/connections/{connection['id']}",
        headers=auth(user),
    )
    assert failed.status_code == 409
    with api_environment["SessionFactory"]() as db:
        stored = db.get(MCPConnection, UUID(connection["id"]))
        assert stored is not None
        assert stored.is_enabled is False

    runtime.fail_invalidation = False
    deleted = api_environment["client"].delete(
        f"/api/mcp/connections/{connection['id']}",
        headers=auth(user),
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    with api_environment["SessionFactory"]() as db:
        assert db.get(MCPConnection, UUID(connection["id"])) is None


def test_openapi_contains_management_routes(api_environment) -> None:
    """Keep every Phase 4 operation visible in generated API documentation."""
    paths = api_environment["client"].get("/openapi.json").json()["paths"]
    expected = {
        "/api/mcp/connections",
        "/api/mcp/connections/{connection_id}",
        "/api/mcp/connections/{connection_id}/enabled",
        "/api/mcp/connections/{connection_id}/test",
        "/api/mcp/connections/{connection_id}/connect",
        "/api/mcp/connections/{connection_id}/disconnect",
        "/api/mcp/connections/{connection_id}/refresh-tools",
        "/api/mcp/connections/{connection_id}/tools",
        "/api/mcp/connections/{connection_id}/tools/{tool_id}",
        "/api/mcp/connections/{connection_id}/tools/{tool_id}/enabled",
    }
    assert expected <= set(paths)
