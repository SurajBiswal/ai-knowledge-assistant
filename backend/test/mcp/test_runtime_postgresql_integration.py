"""Verify MCP authorization row locks against a disposable PostgreSQL database.

The test is opt-in through ``MCP_TEST_POSTGRES_URL`` and refuses database names
without the ``mcp_runtime_test_`` prefix. This prevents accidental execution
against the shared development database.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from types import SimpleNamespace
from typing import Any, Callable

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.mcp.config.server_config import MCPServerConfig
from app.mcp.config.stdio_templates import ApprovedStdioServerTemplate
from app.mcp.runtime import MCPRuntime, MCPRuntimeError
from app.mcp.security.connection_validation import MCPConnectionConfigValidator
from app.models.mcp_connection import MCPConnection
from app.models.mcp_connection_tool import MCPConnectionTool
from app.models.user import User
from app.services.mcp_connection_service import (
    DiscoveredMCPTool,
    MCPConnectionService,
)


ECHO_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
}


class PostgreSQLLockManager:
    """Pause a fake remote call after the runtime has acquired database locks."""

    def __init__(
        self,
        configs: list[MCPServerConfig],
        *,
        call_started: asyncio.Event,
        call_gate: asyncio.Event,
        fail_call: bool = False,
    ) -> None:
        """Store synchronization controls used by the concurrency assertions."""
        self.config = configs[0]
        self.call_started = call_started
        self.call_gate = call_gate
        self.fail_call = fail_call

    async def connect(self, _server_name: str) -> dict[str, Any]:
        """Pretend the transport connected without opening external resources."""
        return {"status": "connected", "tool_count": 1}

    async def discover_tools(self, _server_name: str) -> list[dict[str, Any]]:
        """Return one stable schema whose persisted approval remains valid."""
        return [
            {
                "name": "echo",
                "description": "Echo text.",
                "input_schema": ECHO_SCHEMA,
                "annotations": {"readOnlyHint": True},
            }
        ]

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Hold the authorization lease until the test releases this call."""
        self.call_started.set()
        await self.call_gate.wait()
        if self.fail_call:
            raise RuntimeError("controlled remote failure")
        return SimpleNamespace(
            is_error=False,
            content=[],
            structured_content=None,
            server=server_name,
            tool=tool_name,
            arguments=arguments,
        )

    async def disconnect_all(self) -> None:
        """Provide the cleanup operation expected by the production owner task."""


@pytest.fixture
def postgres_database():
    """Create only the three required tables in an explicitly disposable DB."""
    raw_url = os.getenv("MCP_TEST_POSTGRES_URL")
    if not raw_url:
        pytest.skip("MCP_TEST_POSTGRES_URL is not configured")
    parsed = make_url(raw_url)
    if not (parsed.database or "").startswith("mcp_runtime_test_"):
        pytest.fail("Refusing to use a non-disposable PostgreSQL database")

    engine = create_engine(parsed, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        pytest.fail("MCP_TEST_POSTGRES_URL must use PostgreSQL")
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


def create_approved_connection(SessionFactory, *, suffix: str):
    """Persist one enabled connection and one explicitly approved echo tool."""
    template = ApprovedStdioServerTemplate(
        code="postgres_lock_test",
        name="PostgreSQL Lock Test",
        command="/approved/test/server",
    )
    validator = MCPConnectionConfigValidator(
        stdio_templates={template.code: template},
    )
    with SessionFactory() as db:
        user = User(
            name=f"PostgreSQL {suffix}",
            email=f"postgres-{suffix}@example.test",
            password_hash="test-hash",
        )
        db.add(user)
        db.flush()
        service = MCPConnectionService(db, config_validator=validator)
        details = service.create_connection(
            user_id=user.id,
            name=f"PostgreSQL {suffix}",
            transport="stdio",
            stdio_template_code=template.code,
            timeout_seconds=5,
        )
        connection = db.get(MCPConnection, details.id)
        assert connection is not None
        connection.is_enabled = True
        discovered = service.synchronize_discovered_tools(
            user_id=user.id,
            connection_id=connection.id,
            discovered_tools=[
                DiscoveredMCPTool(
                    name="echo",
                    description="Echo text.",
                    input_schema=ECHO_SCHEMA,
                )
            ],
        )[0]
        service.set_tool_enabled(
            user_id=user.id,
            connection_id=connection.id,
            tool_id=discovered.id,
            enabled=True,
        )
        db.commit()
        return validator, user.id, connection.id, discovered.id


def build_runtime_and_manager(
    SessionFactory,
    *,
    validator: MCPConnectionConfigValidator,
    fail_call: bool = False,
):
    """Build the production runtime around a controllable fake remote server."""
    call_started = asyncio.Event()
    call_gate = asyncio.Event()

    def factory(configs):
        return PostgreSQLLockManager(
            configs,
            call_started=call_started,
            call_gate=call_gate,
            fail_call=fail_call,
        )

    runtime = MCPRuntime(
        session_factory=SessionFactory,
        config_validator=validator,
        manager_factory=factory,
        disconnect_timeout_seconds=0.5,
        shutdown_timeout_seconds=2.0,
    )
    return runtime, call_started, call_gate


async def assert_mutation_waits_for_call(
    *,
    SessionFactory,
    runtime: MCPRuntime,
    call_started: asyncio.Event,
    call_gate: asyncio.Event,
    user_id,
    connection_id,
    tool_id,
    mutate: Callable[[], None],
) -> None:
    """Prove a concurrent update cannot commit while dispatch holds row locks."""
    call = asyncio.create_task(
        runtime.call_tool(
            user_id=user_id,
            connection_id=connection_id,
            tool_id=tool_id,
            arguments={"text": "locked"},
        )
    )
    await asyncio.wait_for(call_started.wait(), timeout=3)
    mutation = asyncio.create_task(asyncio.to_thread(mutate))
    done, _pending = await asyncio.wait({mutation}, timeout=0.25)
    assert not done, "PostgreSQL mutation bypassed the authorization row lock"
    call_gate.set()
    await asyncio.wait_for(call, timeout=3)
    await asyncio.wait_for(mutation, timeout=3)


@pytest.mark.asyncio
async def test_postgresql_disable_waits_for_active_authorized_call(
    postgres_database,
) -> None:
    """Block connection disablement until an already-authorized call finishes."""
    validator, user_id, connection_id, tool_id = create_approved_connection(
        postgres_database,
        suffix="disable",
    )
    runtime, started, gate = build_runtime_and_manager(
        postgres_database,
        validator=validator,
    )

    call = asyncio.create_task(
        runtime.call_tool(
            user_id=user_id,
            connection_id=connection_id,
            tool_id=tool_id,
            arguments={"text": "cross-process lock"},
        )
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=3)
        child_environment = os.environ.copy()
        child_environment["MCP_LOCK_TEST_CONNECTION_ID"] = str(connection_id)
        child_code = """
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["MCP_TEST_POSTGRES_URL"])
with engine.begin() as connection:
    print("READY", flush=True)
    connection.execute(
        text(
            "UPDATE mcp_connections SET is_enabled=false "
            "WHERE id=CAST(:id AS uuid)"
        ),
        {"id": os.environ["MCP_LOCK_TEST_CONNECTION_ID"]},
    )
engine.dispose()
"""
        child = subprocess.Popen(
            [
                sys.executable,
                "-c",
                child_code,
            ],
            env=child_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert child.stdout is not None
        ready = await asyncio.wait_for(
            asyncio.to_thread(child.stdout.readline),
            timeout=3,
        )
        assert ready.strip() == "READY"
        await asyncio.sleep(0.25)
        assert child.poll() is None, (
            "A separate process bypassed the authorization row lock"
        )
        gate.set()
        await asyncio.wait_for(call, timeout=3)
        _stdout, stderr = await asyncio.wait_for(
            asyncio.to_thread(child.communicate),
            timeout=3,
        )
        assert child.returncode == 0, stderr

        with pytest.raises(MCPRuntimeError) as captured:
            await runtime.call_tool(
                user_id=user_id,
                connection_id=connection_id,
                tool_id=tool_id,
            )
        assert captured.value.code == "connection_disabled"
    finally:
        gate.set()
        if not call.done():
            await asyncio.wait_for(call, timeout=3)
        await runtime.shutdown()


@pytest.mark.asyncio
async def test_postgresql_configuration_change_waits_for_active_call(
    postgres_database,
) -> None:
    """Block configuration commits until the current authorization lease ends."""
    validator, user_id, connection_id, tool_id = create_approved_connection(
        postgres_database,
        suffix="configuration",
    )
    runtime, started, gate = build_runtime_and_manager(
        postgres_database,
        validator=validator,
    )

    def change_configuration() -> None:
        with postgres_database() as db:
            connection = db.get(MCPConnection, connection_id)
            assert connection is not None
            connection.timeout_seconds = 6
            db.commit()

    try:
        await assert_mutation_waits_for_call(
            SessionFactory=postgres_database,
            runtime=runtime,
            call_started=started,
            call_gate=gate,
            user_id=user_id,
            connection_id=connection_id,
            tool_id=tool_id,
            mutate=change_configuration,
        )
        assert runtime.status(
            user_id=user_id,
            connection_id=connection_id,
        ).state == "connected"
        await runtime.connect(user_id=user_id, connection_id=connection_id)
    finally:
        gate.set()
        await runtime.shutdown()


@pytest.mark.asyncio
async def test_postgresql_authorization_rollback_releases_mutation(
    postgres_database,
) -> None:
    """Release row locks after a failed call by rolling back the lease session."""
    validator, user_id, connection_id, tool_id = create_approved_connection(
        postgres_database,
        suffix="rollback",
    )
    runtime, started, gate = build_runtime_and_manager(
        postgres_database,
        validator=validator,
        fail_call=True,
    )
    call = asyncio.create_task(
        runtime.call_tool(
            user_id=user_id,
            connection_id=connection_id,
            tool_id=tool_id,
        )
    )
    await asyncio.wait_for(started.wait(), timeout=3)
    gate.set()
    with pytest.raises(MCPRuntimeError) as captured:
        await asyncio.wait_for(call, timeout=3)
    assert captured.value.code == "operation_failed"

    def disable_after_rollback() -> None:
        with postgres_database() as db:
            connection = db.get(MCPConnection, connection_id)
            assert connection is not None
            connection.is_enabled = False
            db.commit()

    await asyncio.wait_for(
        asyncio.to_thread(disable_after_rollback),
        timeout=2,
    )
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_postgresql_lock_timeout_is_bounded_and_rolls_back(
    postgres_database,
) -> None:
    """Honor PostgreSQL lock_timeout while another call holds authorization."""
    validator, user_id, connection_id, tool_id = create_approved_connection(
        postgres_database,
        suffix="timeout",
    )
    runtime, started, gate = build_runtime_and_manager(
        postgres_database,
        validator=validator,
    )
    call = asyncio.create_task(
        runtime.call_tool(
            user_id=user_id,
            connection_id=connection_id,
            tool_id=tool_id,
        )
    )
    await asyncio.wait_for(started.wait(), timeout=3)

    def timed_mutation() -> None:
        with postgres_database() as db:
            db.execute(text("SET LOCAL lock_timeout = '150ms'"))
            connection = db.get(MCPConnection, connection_id)
            assert connection is not None
            connection.is_enabled = False
            db.commit()

    try:
        with pytest.raises(OperationalError):
            await asyncio.wait_for(
                asyncio.to_thread(timed_mutation),
                timeout=2,
            )
        with postgres_database() as db:
            connection = db.get(MCPConnection, connection_id)
            assert connection is not None
            assert connection.is_enabled is True
    finally:
        gate.set()
        await asyncio.wait_for(call, timeout=3)
        await runtime.shutdown()
