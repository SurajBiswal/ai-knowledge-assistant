"""Test the lazy, user-isolated MCP runtime and its security checks."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from types import SimpleNamespace
import sys
import time
from typing import Any

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.mcp.client.http_transport import (
    RestrictedStreamableHTTPTransport,
)
from app.mcp.config.server_config import MCPServerConfig
from app.mcp.config.stdio_templates import ApprovedStdioServerTemplate
from app.mcp.runtime import MCPRuntime, MCPRuntimeError, MCPShutdownError
from app.mcp.security.connection_validation import (
    MCPConnectionConfigValidator,
)
from app.mcp.security.redaction import (
    install_sdk_secret_log_filter,
    remove_sdk_secret_log_filter,
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


ECHO_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
}


def test_sdk_log_filter_redacts_arguments_and_exception_text(caplog) -> None:
    """Prevent active credentials from appearing in third-party debug logs."""
    secret = "sdk-debug-secret"
    installed = install_sdk_secret_log_filter([secret])
    try:
        with caplog.at_level(logging.DEBUG, logger="mcp"):
            try:
                raise RuntimeError(secret)
            except RuntimeError:
                logging.getLogger("mcp").exception(
                    "request headers=%s",
                    {"Authorization": f"Bearer {secret}"},
                )
    finally:
        remove_sdk_secret_log_filter(installed)

    assert secret not in caplog.text
    assert "[REDACTED]" in caplog.text


class FakeOwnerSafeManager:
    """Record lifecycle task IDs while simulating one MCP client manager."""

    def __init__(
        self,
        configs: list[MCPServerConfig],
        *,
        schema: dict[str, Any] | None = None,
        fail_connect: Exception | None = None,
        call_delay: float = 0.0,
        disconnect_delay: float = 0.0,
        connect_gate: asyncio.Event | None = None,
        discovery_gate: asyncio.Event | None = None,
        discovery_started: asyncio.Event | None = None,
        block_discovery_number: int = 1,
        call_gate: asyncio.Event | None = None,
        call_started: asyncio.Event | None = None,
        disconnect_gate: asyncio.Event | None = None,
        disconnect_started: asyncio.Event | None = None,
        suppress_disconnect_cancellation: bool = False,
        tool_result: Any | None = None,
    ) -> None:
        """Store the supplied runtime config and controllable test behavior."""
        self.config = configs[0]
        self.schema = schema or ECHO_SCHEMA
        self.fail_connect = fail_connect
        self.call_delay = call_delay
        self.disconnect_delay = disconnect_delay
        self.connect_gate = connect_gate
        self.discovery_gate = discovery_gate
        self.discovery_started = discovery_started
        self.block_discovery_number = block_discovery_number
        self.call_gate = call_gate
        self.call_started = call_started
        self.disconnect_gate = disconnect_gate
        self.disconnect_started = disconnect_started
        self.suppress_disconnect_cancellation = (
            suppress_disconnect_cancellation
        )
        self.tool_result = tool_result
        # Simulate a client library that copied headers into its own object.
        self.retained_headers = dict(self.config.headers)
        self.task_ids: list[int] = []
        self.call_count = 0
        self.disconnect_count = 0
        self.discovery_count = 0

    def _record_task(self) -> None:
        """Record the current task so the test can prove one-task ownership."""
        task = asyncio.current_task()
        assert task is not None
        self.task_ids.append(id(task))

    async def connect(self, _server_name: str) -> dict[str, Any]:
        """Optionally block or fail while recording the owner task."""
        self._record_task()
        if self.connect_gate is not None:
            await self.connect_gate.wait()
        if self.fail_connect is not None:
            raise self.fail_connect
        return {"status": "connected", "tool_count": 1}

    async def discover_tools(self, _server_name: str) -> list[dict[str, Any]]:
        """Return one predictable remote tool from the owner task."""
        self._record_task()
        self.discovery_count += 1
        if self.discovery_count == self.block_discovery_number:
            if self.discovery_started is not None:
                self.discovery_started.set()
            if self.discovery_gate is not None:
                await self.discovery_gate.wait()
        return [
            {
                "name": "echo",
                "description": "Echo text.",
                "input_schema": self.schema,
                "annotations": {"readOnlyHint": True},
            }
        ]

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Return a simple tool result after an optional controlled delay."""
        self._record_task()
        self.call_count += 1
        if self.call_started is not None:
            self.call_started.set()
        if self.call_gate is not None:
            await self.call_gate.wait()
        if self.call_delay:
            await asyncio.sleep(self.call_delay)
        if self.tool_result is not None:
            return self.tool_result
        return SimpleNamespace(
            is_error=False,
            content=[],
            server=server_name,
            tool=tool_name,
            arguments=arguments,
        )

    async def disconnect_all(self) -> None:
        """Record same-task cleanup and optionally delay it for timeout tests."""
        self._record_task()
        self.disconnect_count += 1
        if self.disconnect_started is not None:
            self.disconnect_started.set()
        try:
            if self.disconnect_gate is not None:
                while True:
                    try:
                        await self.disconnect_gate.wait()
                        break
                    except asyncio.CancelledError:
                        if not self.suppress_disconnect_cancellation:
                            raise
            if self.disconnect_delay:
                await asyncio.sleep(self.disconnect_delay)
        finally:
            self.retained_headers.clear()


@pytest.fixture
def database(tmp_path: Path):
    """Create isolated file-backed tables usable from asyncio worker threads."""
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'runtime.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            MCPConnection.__table__,
            MCPConnectionTool.__table__,
        ],
    )
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield SessionFactory
    finally:
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
def encryption_service() -> CredentialEncryptionService:
    """Use an isolated encryption key that cannot expose real credentials."""
    return CredentialEncryptionService(Fernet.generate_key().decode())


@pytest.fixture
def validator() -> MCPConnectionConfigValidator:
    """Approve only the test Python executable and deterministic public DNS."""
    template = ApprovedStdioServerTemplate(
        code="test_echo",
        name="Test Echo",
        command=sys.executable,
    )
    return MCPConnectionConfigValidator(
        stdio_templates={template.code: template},
        host_resolver=lambda _hostname: {"8.8.8.8"},
    )


def create_user(SessionFactory, *, email: str, name: str) -> User:
    """Persist one test owner and return its detached identity."""
    with SessionFactory() as db:
        user = User(name=name, email=email, password_hash="test-hash")
        db.add(user)
        db.commit()
        return user


def create_connection(
    SessionFactory,
    *,
    validator: MCPConnectionConfigValidator,
    encryption_service: CredentialEncryptionService,
    user_id,
    name: str = "Shared Name",
    enabled: bool = True,
    auth_type: str = "none",
    credentials: dict[str, str] | None = None,
    transport: str = "stdio",
    server_url: str | None = None,
) -> MCPConnection:
    """Persist one connection using Phase 2 validation, then set test enablement."""
    with SessionFactory() as db:
        service = MCPConnectionService(
            db,
            credential_encryption_service=encryption_service,
            config_validator=validator,
        )
        details = service.create_connection(
            user_id=user_id,
            name=name,
            transport=transport,
            stdio_template_code=("test_echo" if transport == "stdio" else None),
            server_url=server_url,
            auth_type=auth_type,
            credentials=credentials,
        )
        connection = db.get(MCPConnection, details.id)
        assert connection is not None
        connection.is_enabled = enabled
        db.commit()
        return connection


def create_approved_tool(
    SessionFactory,
    *,
    validator: MCPConnectionConfigValidator,
    encryption_service: CredentialEncryptionService,
    user_id,
    connection_id,
    enabled: bool = True,
    schema: dict[str, Any] | None = None,
) -> MCPConnectionTool:
    """Persist discovery and explicit approval for one predictable echo tool."""
    with SessionFactory() as db:
        service = MCPConnectionService(
            db,
            credential_encryption_service=encryption_service,
            config_validator=validator,
        )
        details = service.synchronize_discovered_tools(
            user_id=user_id,
            connection_id=connection_id,
            discovered_tools=[
                DiscoveredMCPTool(
                    name="echo",
                    description="Echo text.",
                    input_schema=schema or ECHO_SCHEMA,
                )
            ],
        )[0]
        if enabled:
            service.set_tool_enabled(
                user_id=user_id,
                connection_id=connection_id,
                tool_id=details.id,
                enabled=True,
            )
        db.commit()
        tool = db.get(MCPConnectionTool, details.id)
        assert tool is not None
        return tool


def build_runtime(
    SessionFactory,
    *,
    validator,
    encryption_service,
    factory,
    disconnect_timeout_seconds: float = 0.2,
    shutdown_timeout_seconds: float = 0.5,
    remote_http_egress_protected: bool = False,
) -> MCPRuntime:
    """Build the production runtime with test database and manager factories."""
    return MCPRuntime(
        session_factory=SessionFactory,
        config_validator=validator,
        credential_encryption_service=encryption_service,
        manager_factory=factory,
        disconnect_timeout_seconds=disconnect_timeout_seconds,
        shutdown_timeout_seconds=shutdown_timeout_seconds,
        remote_http_egress_protected=remote_http_egress_protected,
    )


@pytest.mark.asyncio
async def test_same_connection_name_is_isolated_by_user_and_id(
    database,
    validator,
    encryption_service,
) -> None:
    """Keep two owners separate even when their friendly names are identical."""
    user_a = create_user(database, email="a@example.test", name="A")
    user_b = create_user(database, email="b@example.test", name="B")
    connection_a = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user_a.id,
    )
    connection_b = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user_b.id,
    )
    managers: list[FakeOwnerSafeManager] = []

    def factory(configs):
        manager = FakeOwnerSafeManager(configs)
        managers.append(manager)
        return manager

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    try:
        await runtime.connect(user_id=user_a.id, connection_id=connection_a.id)
        await runtime.connect(user_id=user_b.id, connection_id=connection_b.id)
        assert len(managers) == 2
        assert managers[0].config.name == str(connection_a.id)
        assert managers[1].config.name == str(connection_b.id)
        assert runtime.status(
            user_id=user_a.id,
            connection_id=connection_a.id,
        ).state == "connected"
        assert runtime.status(
            user_id=user_b.id,
            connection_id=connection_b.id,
        ).state == "connected"
    finally:
        await runtime.shutdown()


@pytest.mark.asyncio
async def test_concurrent_startup_creates_only_one_client(
    database,
    validator,
    encryption_service,
) -> None:
    """Serialize simultaneous starts for the same user and connection."""
    user = create_user(database, email="one@example.test", name="One")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
    )
    gate = asyncio.Event()
    managers: list[FakeOwnerSafeManager] = []

    def factory(configs):
        manager = FakeOwnerSafeManager(configs, connect_gate=gate)
        managers.append(manager)
        return manager

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    first = asyncio.create_task(
        runtime.connect(user_id=user.id, connection_id=connection.id)
    )
    second = asyncio.create_task(
        runtime.connect(user_id=user.id, connection_id=connection.id)
    )
    await asyncio.sleep(0.05)
    gate.set()
    try:
        await asyncio.gather(first, second)
        assert len(managers) == 1
    finally:
        await runtime.shutdown()


@pytest.mark.asyncio
async def test_owner_task_handles_connect_call_and_disconnect(
    database,
    validator,
    encryption_service,
) -> None:
    """Prove every SDK lifecycle operation runs in one dedicated task."""
    user = create_user(database, email="owner@example.test", name="Owner")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
    )
    tool = create_approved_tool(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        connection_id=connection.id,
    )
    managers: list[FakeOwnerSafeManager] = []

    def factory(configs):
        manager = FakeOwnerSafeManager(configs)
        managers.append(manager)
        return manager

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    await runtime.call_tool(
        user_id=user.id,
        connection_id=connection.id,
        tool_id=tool.id,
        arguments={"text": "hello"},
    )
    await runtime.disconnect(user_id=user.id, connection_id=connection.id)

    assert managers[0].call_count == 1
    assert managers[0].disconnect_count == 1
    assert len(set(managers[0].task_ids)) == 1


@pytest.mark.asyncio
async def test_startup_failure_can_reconnect_without_leaking_secret(
    database,
    validator,
    encryption_service,
) -> None:
    """Discard failed state, return a safe error, and permit a later retry."""
    user = create_user(database, email="retry@example.test", name="Retry")
    secret = "runtime-only-secret-token"
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        transport="streamable_http",
        server_url="https://mcp.example.test/mcp",
        auth_type="bearer",
        credentials={"token": secret},
    )
    managers: list[FakeOwnerSafeManager] = []

    def factory(configs):
        failure = (
            RuntimeError(f"provider printed {secret}")
            if not managers
            else None
        )
        manager = FakeOwnerSafeManager(configs, fail_connect=failure)
        managers.append(manager)
        return manager

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
        remote_http_egress_protected=True,
    )
    with pytest.raises(MCPRuntimeError) as captured:
        await runtime.connect(user_id=user.id, connection_id=connection.id)
    assert captured.value.code == "connection_failed"
    assert secret not in str(captured.value)
    assert secret not in repr(captured.value)
    assert secret not in repr(managers[0].config)

    connected = await runtime.connect(
        user_id=user.id,
        connection_id=connection.id,
    )
    assert connected.state == "connected"
    assert len(managers) == 2
    assert managers[1].config.headers == {
        "Authorization": f"Bearer {secret}"
    }
    await runtime.shutdown()
    assert managers[1].config.headers == {}


@pytest.mark.asyncio
async def test_tool_timeout_and_shutdown_are_bounded(
    database,
    validator,
    encryption_service,
) -> None:
    """Bound a hanging tool call and slow disconnect without hanging shutdown."""
    user = create_user(database, email="timeout@example.test", name="Timeout")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
    )
    tool = create_approved_tool(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        connection_id=connection.id,
    )
    with database() as db:
        stored = db.get(MCPConnection, connection.id)
        assert stored is not None
        stored.timeout_seconds = 0.05
        db.commit()

    def factory(configs):
        return FakeOwnerSafeManager(
            configs,
            call_delay=1.0,
            disconnect_delay=1.0,
        )

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
        disconnect_timeout_seconds=0.05,
        shutdown_timeout_seconds=0.15,
    )
    with pytest.raises(MCPRuntimeError) as captured:
        await runtime.call_tool(
            user_id=user.id,
            connection_id=connection.id,
            tool_id=tool.id,
            arguments={},
        )
    assert captured.value.code == "operation_timeout"

    started = time.monotonic()
    await runtime.shutdown()
    assert time.monotonic() - started < 0.5


@pytest.mark.asyncio
async def test_disabled_connection_and_tool_are_rejected_before_start(
    database,
    validator,
    encryption_service,
) -> None:
    """Enforce persisted connection and tool approval before network access."""
    user = create_user(database, email="disabled@example.test", name="Disabled")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        enabled=False,
    )
    factory_calls = 0

    def factory(configs):
        nonlocal factory_calls
        factory_calls += 1
        return FakeOwnerSafeManager(configs)

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    with pytest.raises(MCPRuntimeError) as disabled_connection:
        await runtime.connect(user_id=user.id, connection_id=connection.id)
    assert disabled_connection.value.code == "connection_disabled"

    with database() as db:
        stored = db.get(MCPConnection, connection.id)
        assert stored is not None
        stored.is_enabled = True
        db.commit()
    tool = create_approved_tool(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        connection_id=connection.id,
        enabled=False,
    )
    with pytest.raises(MCPRuntimeError) as disabled_tool:
        await runtime.call_tool(
            user_id=user.id,
            connection_id=connection.id,
            tool_id=tool.id,
        )
    assert disabled_tool.value.code == "tool_disabled"
    assert factory_calls == 0


@pytest.mark.asyncio
async def test_changed_schema_revokes_approval_before_execution(
    database,
    validator,
    encryption_service,
) -> None:
    """Synchronize live discovery and stop a previously approved changed tool."""
    user = create_user(database, email="schema@example.test", name="Schema")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
    )
    tool = create_approved_tool(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        connection_id=connection.id,
    )
    changed_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "uppercase": {"type": "boolean"},
        },
    }
    managers: list[FakeOwnerSafeManager] = []

    def factory(configs):
        manager = FakeOwnerSafeManager(configs, schema=changed_schema)
        managers.append(manager)
        return manager

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    try:
        with pytest.raises(MCPRuntimeError) as captured:
            await runtime.call_tool(
                user_id=user.id,
                connection_id=connection.id,
                tool_id=tool.id,
            )
        assert captured.value.code == "tool_disabled"
        assert managers[0].call_count == 0
    finally:
        await runtime.shutdown()


@pytest.mark.asyncio
async def test_http_destination_is_revalidated_immediately_before_connect(
    database,
    encryption_service,
) -> None:
    """Reject a hostname that changes from public to private after persistence."""
    addresses = {"8.8.8.8"}
    validator = MCPConnectionConfigValidator(
        host_resolver=lambda _hostname: addresses,
    )
    user = create_user(database, email="ssrf@example.test", name="SSRF")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        transport="streamable_http",
        server_url="https://mcp.example.test/mcp",
    )
    factory_calls = 0

    def factory(configs):
        nonlocal factory_calls
        factory_calls += 1
        return FakeOwnerSafeManager(configs)

    addresses.clear()
    addresses.add("127.0.0.1")
    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    with pytest.raises(MCPRuntimeError) as captured:
        await runtime.connect(user_id=user.id, connection_id=connection.id)
    assert captured.value.code == "configuration_invalid"
    assert factory_calls == 0


@pytest.mark.asyncio
async def test_remote_http_requires_deployment_egress_gate(
    database,
    validator,
    encryption_service,
) -> None:
    """Keep arbitrary user-supplied HTTP servers off unless egress is protected."""
    user = create_user(database, email="gate@example.test", name="Gate")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        transport="streamable_http",
        server_url="https://mcp.example.test/mcp",
    )
    factory_calls = 0

    def factory(configs):
        nonlocal factory_calls
        factory_calls += 1
        return FakeOwnerSafeManager(configs)

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    with pytest.raises(MCPRuntimeError) as captured:
        await runtime.connect(user_id=user.id, connection_id=connection.id)
    assert captured.value.code == "remote_http_disabled"
    assert factory_calls == 0


@pytest.mark.asyncio
async def test_connection_disabled_during_discovery_is_denied_before_call(
    database,
    validator,
    encryption_service,
) -> None:
    """Recheck a connection changed by another worker while discovery runs."""
    user = create_user(database, email="race-disable@example.test", name="Race")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
    )
    tool = create_approved_tool(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        connection_id=connection.id,
    )
    discovery_started = asyncio.Event()
    discovery_gate = asyncio.Event()
    manager: FakeOwnerSafeManager | None = None

    def factory(configs):
        nonlocal manager
        manager = FakeOwnerSafeManager(
            configs,
            discovery_started=discovery_started,
            discovery_gate=discovery_gate,
            block_discovery_number=2,
        )
        return manager

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    try:
        await runtime.connect(user_id=user.id, connection_id=connection.id)
        call = asyncio.create_task(
            runtime.call_tool(
                user_id=user.id,
                connection_id=connection.id,
                tool_id=tool.id,
            )
        )
        await asyncio.wait_for(discovery_started.wait(), timeout=1)
        with database() as db:
            stored = db.get(MCPConnection, connection.id)
            assert stored is not None
            stored.is_enabled = False
            db.commit()
        discovery_gate.set()
        with pytest.raises(MCPRuntimeError) as captured:
            await call
        assert captured.value.code == "connection_disabled"
        assert manager is not None
        assert manager.call_count == 0
    finally:
        discovery_gate.set()
        await runtime.shutdown()


@pytest.mark.asyncio
async def test_configuration_mutation_immediately_before_dispatch_is_denied(
    database,
    validator,
    encryption_service,
) -> None:
    """Reject a fingerprint change at the final row-lock authorization check."""
    user = create_user(database, email="race-config@example.test", name="Race")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
    )
    tool = create_approved_tool(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        connection_id=connection.id,
    )
    manager: FakeOwnerSafeManager | None = None

    def factory(configs):
        nonlocal manager
        manager = FakeOwnerSafeManager(configs)
        return manager

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    original_lease = runtime._authorization_lease
    mutation_done = False

    @asynccontextmanager
    async def mutate_then_authorize(**kwargs):
        nonlocal mutation_done
        if not mutation_done:
            with database() as db:
                stored = db.get(MCPConnection, connection.id)
                assert stored is not None
                stored.timeout_seconds += 1
                db.commit()
            mutation_done = True
        async with original_lease(**kwargs) as approved:
            yield approved

    runtime._authorization_lease = mutate_then_authorize  # type: ignore[method-assign]
    try:
        with pytest.raises(MCPRuntimeError) as captured:
            await runtime.call_tool(
                user_id=user.id,
                connection_id=connection.id,
                tool_id=tool.id,
            )
        assert captured.value.code == "configuration_changed"
        assert manager is not None
        assert manager.call_count == 0
    finally:
        await runtime.shutdown()


@pytest.mark.asyncio
async def test_tool_disable_immediately_before_dispatch_is_denied(
    database,
    validator,
    encryption_service,
) -> None:
    """Recheck explicit tool approval at the last dispatch boundary."""
    user = create_user(database, email="race-tool@example.test", name="Race")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
    )
    tool = create_approved_tool(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        connection_id=connection.id,
    )
    manager: FakeOwnerSafeManager | None = None

    def factory(configs):
        nonlocal manager
        manager = FakeOwnerSafeManager(configs)
        return manager

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    original_lease = runtime._authorization_lease

    @asynccontextmanager
    async def disable_then_authorize(**kwargs):
        with database() as db:
            stored = db.get(MCPConnectionTool, tool.id)
            assert stored is not None
            stored.is_enabled = False
            db.commit()
        async with original_lease(**kwargs) as approved:
            yield approved

    runtime._authorization_lease = disable_then_authorize  # type: ignore[method-assign]
    try:
        with pytest.raises(MCPRuntimeError) as captured:
            await runtime.call_tool(
                user_id=user.id,
                connection_id=connection.id,
                tool_id=tool.id,
            )
        assert captured.value.code == "tool_disabled"
        assert manager is not None
        assert manager.call_count == 0
    finally:
        await runtime.shutdown()


@pytest.mark.asyncio
async def test_tool_result_redacts_credentials_from_text_and_structure(
    database,
    validator,
    encryption_service,
) -> None:
    """Remove a malicious server's copy of its configured bearer credential."""
    user = create_user(database, email="redact@example.test", name="Redact")
    secret = "maliciously-reflected-secret"
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        transport="streamable_http",
        server_url="https://mcp.example.test/mcp",
        auth_type="bearer",
        credentials={"token": secret},
    )
    tool = create_approved_tool(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        connection_id=connection.id,
    )
    malicious = SimpleNamespace(
        is_error=False,
        content=[SimpleNamespace(text=f"stolen {secret}")],
        structured_content={
            "nested": {
                "credential": secret,
                f"reflected-{secret}": "also unsafe",
            }
        },
    )

    def factory(configs):
        return FakeOwnerSafeManager(configs, tool_result=malicious)

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
        remote_http_egress_protected=True,
    )
    try:
        result = await runtime.call_tool(
            user_id=user.id,
            connection_id=connection.id,
            tool_id=tool.id,
        )
        assert secret not in result.content[0].text
        assert result.content[0].text == "stolen [REDACTED]"
        assert result.structured_content == {
            "nested": {
                "credential": "[REDACTED]",
                "reflected-[REDACTED]": "also unsafe",
            }
        }
    finally:
        await runtime.shutdown()


@pytest.mark.asyncio
async def test_discovery_redacts_credentials_before_persistence(
    database,
    validator,
    encryption_service,
) -> None:
    """Remove a reflected bearer token from every public discovery field."""
    user = create_user(
        database,
        email="discovery-redact@example.test",
        name="Discovery Redact",
    )
    secret = "reflected-discovery-secret"
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        transport="streamable_http",
        server_url="https://mcp.example.test/mcp",
        auth_type="bearer",
        credentials={"token": secret},
    )

    class MaliciousDiscoveryManager(FakeOwnerSafeManager):
        """Simulate a server that repeats its bearer token in discovery."""

        async def discover_tools(self, _server_name: str):
            self._record_task()
            return [
                {
                    "name": "echo",
                    "description": f"stolen {secret}",
                    "input_schema": {
                        "type": "object",
                        "description": secret,
                    },
                    "annotations": {
                        "credential": secret,
                        f"reflected-{secret}": True,
                    },
                }
            ]

    def factory(configs):
        return MaliciousDiscoveryManager(configs)

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
        remote_http_egress_protected=True,
    )
    try:
        tools = await runtime.refresh_tools(
            user_id=user.id,
            connection_id=connection.id,
        )
        assert len(tools) == 1
        serialized = repr(tools[0])
        assert secret not in serialized
        assert "[REDACTED]" in serialized

        with database() as db:
            stored = db.query(MCPConnectionTool).one()
            assert secret not in repr(
                {
                    "description": stored.description,
                    "input_schema": stored.input_schema,
                    "annotations": stored.server_annotations,
                }
            )
    finally:
        await runtime.shutdown()


@pytest.mark.asyncio
async def test_new_call_is_rejected_once_shutdown_begins(
    database,
    validator,
    encryption_service,
) -> None:
    """Do not reuse an existing entry after the runtime starts closing."""
    user = create_user(database, email="closing@example.test", name="Closing")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
    )
    tool = create_approved_tool(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        connection_id=connection.id,
    )
    disconnect_started = asyncio.Event()
    disconnect_gate = asyncio.Event()

    def factory(configs):
        return FakeOwnerSafeManager(
            configs,
            disconnect_started=disconnect_started,
            disconnect_gate=disconnect_gate,
        )

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    await runtime.connect(user_id=user.id, connection_id=connection.id)
    shutdown = asyncio.create_task(runtime.shutdown())
    await asyncio.wait_for(disconnect_started.wait(), timeout=1)
    with pytest.raises(MCPRuntimeError) as captured:
        await runtime.call_tool(
            user_id=user.id,
            connection_id=connection.id,
            tool_id=tool.id,
        )
    assert captured.value.code == "runtime_stopped"
    disconnect_gate.set()
    await shutdown


@pytest.mark.asyncio
async def test_shutdown_cancels_active_call_and_closes_owner(
    database,
    validator,
    encryption_service,
) -> None:
    """Cancel an active remote call without losing its owner from tracking."""
    user = create_user(database, email="active@example.test", name="Active")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
    )
    tool = create_approved_tool(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        connection_id=connection.id,
    )
    call_started = asyncio.Event()
    call_gate = asyncio.Event()

    def factory(configs):
        return FakeOwnerSafeManager(
            configs,
            call_started=call_started,
            call_gate=call_gate,
        )

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    call = asyncio.create_task(
        runtime.call_tool(
            user_id=user.id,
            connection_id=connection.id,
            tool_id=tool.id,
        )
    )
    await asyncio.wait_for(call_started.wait(), timeout=1)
    await runtime.shutdown()
    with pytest.raises(MCPRuntimeError) as captured:
        await call
    assert captured.value.code == "runtime_stopped"
    assert runtime._owner_tasks == set()


@pytest.mark.asyncio
async def test_cancelled_disconnect_does_not_hide_owner_from_shutdown(
    database,
    validator,
    encryption_service,
) -> None:
    """Keep tracking an owner when the task waiting for disconnect is cancelled."""
    user = create_user(database, email="cancel@example.test", name="Cancel")
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
    )
    disconnect_started = asyncio.Event()
    disconnect_gate = asyncio.Event()

    def factory(configs):
        return FakeOwnerSafeManager(
            configs,
            disconnect_started=disconnect_started,
            disconnect_gate=disconnect_gate,
        )

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
    )
    await runtime.connect(user_id=user.id, connection_id=connection.id)
    disconnect = asyncio.create_task(
        runtime.disconnect(user_id=user.id, connection_id=connection.id)
    )
    await asyncio.wait_for(disconnect_started.wait(), timeout=1)
    disconnect.cancel()
    with pytest.raises(asyncio.CancelledError):
        await disconnect
    assert runtime._owner_tasks
    assert (user.id, connection.id) in runtime._entries
    disconnect_gate.set()
    await runtime.shutdown()
    assert runtime._owner_tasks == set()


@pytest.mark.asyncio
async def test_shutdown_reports_cancellation_resistant_owner_by_deadline(
    database,
    validator,
    encryption_service,
) -> None:
    """Retry cleanup while closing after a survivor retained copied credentials."""
    user = create_user(database, email="stubborn@example.test", name="Stubborn")
    secret = "retained-until-owner-finishes"
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        transport="streamable_http",
        server_url="https://mcp.example.test/mcp",
        auth_type="bearer",
        credentials={"token": secret},
    )
    disconnect_gate = asyncio.Event()
    managers: list[FakeOwnerSafeManager] = []

    def factory(configs):
        manager = FakeOwnerSafeManager(
            configs,
            disconnect_gate=disconnect_gate,
            suppress_disconnect_cancellation=True,
        )
        managers.append(manager)
        return manager

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
        disconnect_timeout_seconds=0.03,
        shutdown_timeout_seconds=0.1,
        remote_http_egress_protected=True,
    )
    await runtime.connect(user_id=user.id, connection_id=connection.id)
    started = time.monotonic()
    with pytest.raises(MCPShutdownError) as captured:
        await runtime.shutdown()
    assert time.monotonic() - started < 0.3
    assert captured.value.survivor_count == 1
    assert runtime._owner_tasks
    assert runtime._closing is True
    assert managers[0].retained_headers == {
        "Authorization": f"Bearer {secret}"
    }

    disconnect_gate.set()
    await asyncio.sleep(0.05)
    await runtime.shutdown()
    assert runtime._owner_tasks == set()
    assert managers[0].retained_headers == {}


@pytest.mark.asyncio
async def test_cancelled_shutdown_cleanup_clears_runtime_credentials(
    database,
    validator,
    encryption_service,
) -> None:
    """Clear header copies when shutdown cancels a blocked cleanup operation."""
    user = create_user(database, email="clear@example.test", name="Clear")
    secret = "clear-me-on-cancellation"
    connection = create_connection(
        database,
        validator=validator,
        encryption_service=encryption_service,
        user_id=user.id,
        transport="streamable_http",
        server_url="https://mcp.example.test/mcp",
        auth_type="bearer",
        credentials={"token": secret},
    )
    disconnect_gate = asyncio.Event()
    managers: list[FakeOwnerSafeManager] = []

    def factory(configs):
        manager = FakeOwnerSafeManager(
            configs,
            disconnect_gate=disconnect_gate,
        )
        managers.append(manager)
        return manager

    runtime = build_runtime(
        database,
        validator=validator,
        encryption_service=encryption_service,
        factory=factory,
        disconnect_timeout_seconds=0.03,
        shutdown_timeout_seconds=0.1,
        remote_http_egress_protected=True,
    )
    await runtime.connect(user_id=user.id, connection_id=connection.id)
    assert managers[0].config.headers
    await runtime.shutdown()
    assert managers[0].config.headers == {}
    assert secret not in repr(runtime._entries)


@pytest.mark.asyncio
async def test_http_transport_disables_redirects_and_environment_proxies(
    monkeypatch,
) -> None:
    """Pass redirect-rejecting settings to the HTTP client used by MCP."""
    from app.mcp.client import http_transport as transport_module

    captured: dict[str, Any] = {}

    class FakeHTTPClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

    @asynccontextmanager
    async def fake_streamable_http_client(_url, *, http_client):
        assert isinstance(http_client, FakeHTTPClient)
        yield (SimpleNamespace(), SimpleNamespace())

    monkeypatch.setattr(transport_module.httpx2, "AsyncClient", FakeHTTPClient)
    monkeypatch.setattr(
        transport_module,
        "streamable_http_client",
        fake_streamable_http_client,
    )
    transport = RestrictedStreamableHTTPTransport(
        url="https://mcp.example.test/mcp",
        headers={"Authorization": "Bearer secret"},
    )
    async with transport:
        pass

    assert captured["follow_redirects"] is False
    assert captured["max_redirects"] == 0
    assert captured["trust_env"] is False


@pytest.mark.asyncio
async def test_fastapi_lifespan_creates_idle_runtime_and_shuts_it_down() -> None:
    """Create no client at startup and close the empty runtime on shutdown."""
    from app.main import app, lifespan

    async with lifespan(app):
        runtime = app.state.mcp_runtime
        assert isinstance(runtime, MCPRuntime)
        assert runtime._entries == {}
    assert runtime._closing is True
