"""Exercise the Phase 3 owner-task runtime with a real stdio MCP process."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import signal
import sys
import time

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.mcp.config.stdio_templates import ApprovedStdioServerTemplate
from app.mcp.runtime import MCPRuntime, MCPRuntimeError
from app.mcp.security.connection_validation import (
    MCPConnectionConfigValidator,
)
from app.models.mcp_connection import MCPConnection
from app.models.mcp_connection_tool import MCPConnectionTool
from app.models.user import User
from app.services.credential_encryption_service import (
    CredentialEncryptionService,
)
from app.services.mcp_connection_service import MCPConnectionService


TEST_TIMEOUT_SECONDS = 30.0
PROCESS_EXIT_TIMEOUT_SECONDS = 3.0


def _process_exists(pid: int) -> bool:
    """Ask the operating system whether the stdio child PID still exists."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


async def _wait_for_process_exit(pid: int) -> bool:
    """Wait briefly for SDK cleanup to terminate and reap the child process."""
    deadline = time.monotonic() + PROCESS_EXIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if not _process_exists(pid):
            return True
        await asyncio.sleep(0.05)
    return not _process_exists(pid)


async def _exercise_owner_task_runtime(tmp_path: Path) -> None:
    """Persist, lazily start, approve, invoke, and close a real MCP server."""
    server_script = Path(__file__).parent / "servers" / "echo_server.py"
    pid_file = tmp_path / "runtime_echo.pid"
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'runtime_stdio.db'}",
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
    encryption = CredentialEncryptionService(Fernet.generate_key().decode())
    template = ApprovedStdioServerTemplate(
        code="real_runtime_echo",
        name="Real Runtime Echo",
        command=sys.executable,
        fixed_args=(str(server_script),),
        fixed_environment={"MCP_TEST_PID_FILE": str(pid_file)},
    )
    validator = MCPConnectionConfigValidator(
        stdio_templates={template.code: template},
    )

    with SessionFactory() as db:
        user = User(
            name="Runtime Integration User",
            email="runtime-integration@example.test",
            password_hash="test-hash",
        )
        db.add(user)
        db.flush()
        service = MCPConnectionService(
            db,
            credential_encryption_service=encryption,
            config_validator=validator,
        )
        details = service.create_connection(
            user_id=user.id,
            name="Real Runtime Echo",
            transport="stdio",
            stdio_template_code=template.code,
            timeout_seconds=10,
        )
        connection = db.get(MCPConnection, details.id)
        assert connection is not None
        connection.is_enabled = True
        db.commit()
        user_id = user.id
        connection_id = connection.id

    runtime = MCPRuntime(
        session_factory=SessionFactory,
        config_validator=validator,
        credential_encryption_service=encryption,
        disconnect_timeout_seconds=5.0,
        shutdown_timeout_seconds=10.0,
    )
    child_pid: int | None = None
    try:
        connected = await runtime.connect(
            user_id=user_id,
            connection_id=connection_id,
        )
        assert connected.state == "connected"
        assert connected.tool_count == 1
        child_pid = int(pid_file.read_text(encoding="utf-8"))
        assert _process_exists(child_pid)

        # New discovery is intentionally disabled. This explicit update stands
        # in for the future management API that the user will approve later.
        with SessionFactory() as db:
            service = MCPConnectionService(
                db,
                credential_encryption_service=encryption,
                config_validator=validator,
            )
            tool = service.list_tools(
                user_id=user_id,
                connection_id=connection_id,
            )[0]
            approved = service.set_tool_enabled(
                user_id=user_id,
                connection_id=connection_id,
                tool_id=tool.id,
                enabled=True,
            )
            db.commit()
            tool_id = approved.id

        result = await runtime.call_tool(
            user_id=user_id,
            connection_id=connection_id,
            tool_id=tool_id,
            arguments={"text": "hello from owner task"},
        )
        assert result.is_error is False
        assert result.content[0].text == "Echo: hello from owner task"

        await runtime.disconnect(
            user_id=user_id,
            connection_id=connection_id,
        )
        assert runtime.status(
            user_id=user_id,
            connection_id=connection_id,
        ).state == "disconnected"
    finally:
        await runtime.shutdown()
        if child_pid is None and pid_file.exists():
            child_pid = int(pid_file.read_text(encoding="utf-8"))
        if child_pid is not None:
            exited = await _wait_for_process_exit(child_pid)
            if not exited and _process_exists(child_pid):
                os.kill(child_pid, signal.SIGTERM)
            assert exited, "Runtime owner task left the stdio child alive"
        Base.metadata.drop_all(
            engine,
            tables=[
                MCPConnectionTool.__table__,
                MCPConnection.__table__,
                User.__table__,
            ],
        )
        engine.dispose()


@pytest.mark.asyncio
async def test_real_stdio_process_runs_inside_owner_task_runtime(
    tmp_path: Path,
) -> None:
    """Prove the production lifecycle works with MCP 2.3.0 and cleans up."""
    await asyncio.wait_for(
        _exercise_owner_task_runtime(tmp_path),
        timeout=TEST_TIMEOUT_SECONDS,
    )


@pytest.mark.asyncio
async def test_timed_out_blocking_stdio_tool_terminates_child_process(
    tmp_path: Path,
) -> None:
    """Prove a blocked real child is gone after the runtime cancels its owner."""
    server_script = Path(__file__).parent / "servers" / "blocking_server.py"
    pid_file = tmp_path / "blocking_runtime.pid"
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'blocking_runtime.db'}",
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
    encryption = CredentialEncryptionService(Fernet.generate_key().decode())
    template = ApprovedStdioServerTemplate(
        code="blocking_runtime",
        name="Blocking Runtime",
        command=sys.executable,
        fixed_args=(str(server_script),),
        fixed_environment={"MCP_TEST_PID_FILE": str(pid_file)},
    )
    validator = MCPConnectionConfigValidator(
        stdio_templates={template.code: template},
    )

    with SessionFactory() as db:
        user = User(
            name="Blocking Runtime User",
            email="blocking-runtime@example.test",
            password_hash="test-hash",
        )
        db.add(user)
        db.flush()
        service = MCPConnectionService(
            db,
            credential_encryption_service=encryption,
            config_validator=validator,
        )
        details = service.create_connection(
            user_id=user.id,
            name="Blocking Runtime",
            transport="stdio",
            stdio_template_code=template.code,
            # MCP SDK process startup can exceed one second when the complete
            # suite is busy. Three seconds remains bounded while allowing the
            # test to reach the blocking tool call it is meant to exercise.
            timeout_seconds=3,
        )
        connection = db.get(MCPConnection, details.id)
        assert connection is not None
        connection.is_enabled = True
        db.commit()
        user_id = user.id
        connection_id = connection.id

    runtime = MCPRuntime(
        session_factory=SessionFactory,
        config_validator=validator,
        credential_encryption_service=encryption,
        disconnect_timeout_seconds=1.0,
        shutdown_timeout_seconds=3.0,
    )
    child_pid: int | None = None
    try:
        await runtime.connect(user_id=user_id, connection_id=connection_id)
        child_pid = int(pid_file.read_text(encoding="utf-8"))
        with SessionFactory() as db:
            service = MCPConnectionService(
                db,
                credential_encryption_service=encryption,
                config_validator=validator,
            )
            tool = service.list_tools(
                user_id=user_id,
                connection_id=connection_id,
            )[0]
            approved = service.set_tool_enabled(
                user_id=user_id,
                connection_id=connection_id,
                tool_id=tool.id,
                enabled=True,
            )
            db.commit()

        started = time.monotonic()
        with pytest.raises(MCPRuntimeError) as captured:
            await asyncio.wait_for(
                runtime.call_tool(
                    user_id=user_id,
                    connection_id=connection_id,
                    tool_id=approved.id,
                ),
                timeout=8.0,
            )
        assert captured.value.code == "operation_timeout"
        assert time.monotonic() - started < 8.0
        assert await _wait_for_process_exit(child_pid)
    finally:
        await runtime.shutdown()
        if child_pid is not None and _process_exists(child_pid):
            os.kill(child_pid, signal.SIGTERM)
        Base.metadata.drop_all(
            engine,
            tables=[
                MCPConnectionTool.__table__,
                MCPConnection.__table__,
                User.__table__,
            ],
        )
        engine.dispose()
