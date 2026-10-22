"""Own live MCP clients without mixing process state into database records.

``MCPRuntime`` is created by FastAPI's lifespan and remains empty at startup.
The first authorized operation for a connection starts one dedicated owner
task. That task opens, uses, and closes the MCP SDK client, which satisfies the
SDK 2.3.0 rule that AnyIO cancellation scopes must exit in the task that
entered them.

Database status is only last-known information. Current liveness comes from
this process-local runtime. HTTP destinations are revalidated before every
connection and tool call, but deployment-level outbound network restrictions
are still required to fully defend against DNS rebinding and network changes.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import hashlib
import json
import threading
from typing import Any, Literal
from uuid import UUID

import anyio
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mcp.client.manager import MCPClientManager
from app.mcp.config.server_config import MCPServerConfig
from app.mcp.security.connection_validation import (
    MCPConnectionConfigValidator,
    ValidatedMCPConnectionConfig,
)
from app.mcp.security.redaction import (
    install_sdk_secret_log_filter,
    redact_json_value,
    redact_mcp_tool_result,
    remove_sdk_secret_log_filter,
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
from app.services.mcp_connection_service import (
    DiscoveredMCPTool,
    MCPConnectionService,
    MCPToolDetails,
)


RuntimeKey = tuple[UUID, UUID]
ManagerFactory = Callable[[list[MCPServerConfig]], MCPClientManager]
SessionFactory = Callable[[], Session]

DEFAULT_DISCONNECT_TIMEOUT_SECONDS = 5.0
DEFAULT_SHUTDOWN_TIMEOUT_SECONDS = 10.0


class MCPRuntimeError(RuntimeError):
    """Return a stable safe error code without exposing SDK or secret details."""

    def __init__(self, code: str, message: str) -> None:
        """Store a machine-readable code and a credential-free message."""
        super().__init__(message)
        self.code = code


class MCPShutdownError(MCPRuntimeError):
    """Report owner tasks that survived the configured shutdown deadline."""

    def __init__(self, survivor_count: int) -> None:
        """Expose only a count; task details may contain sensitive state."""
        super().__init__(
            "shutdown_incomplete",
            f"MCP shutdown ended with {survivor_count} live owner task(s).",
        )
        self.survivor_count = survivor_count


@dataclass(frozen=True, slots=True)
class MCPRuntimeStatus:
    """Describe current process-local state rather than persisted readiness."""

    user_id: UUID
    connection_id: UUID
    state: Literal["connected", "disconnected", "starting", "stopping"]
    tool_count: int = 0


@dataclass(frozen=True, slots=True)
class _ConnectionSnapshot:
    """Copy validated database fields so no ORM object crosses async tasks."""

    user_id: UUID
    connection_id: UUID
    name: str
    validated: ValidatedMCPConnectionConfig
    auth_type: str
    encrypted_credentials: str | None
    timeout_seconds: float
    fingerprint: str


@dataclass(frozen=True, slots=True)
class _ToolSnapshot:
    """Copy the approval fields checked immediately before remote execution."""

    id: UUID
    remote_name: str
    schema_hash: str


@dataclass(slots=True)
class _OwnerCommand:
    """Carry one operation from an API task to the SDK owner task."""

    operation: Literal["discover", "call", "stop"]
    future: asyncio.Future[Any]
    timeout_seconds: float
    tool_name: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class _RuntimeEntry:
    """Keep one user's live connection and its owner-task communication state."""

    key: RuntimeKey
    fingerprint: str
    queue: asyncio.Queue[_OwnerCommand]
    ready: asyncio.Future[list[dict[str, Any]]]
    closed: asyncio.Event
    task: asyncio.Task[None] | None = None
    state: Literal["starting", "connected", "stopping"] = "starting"
    tools: dict[str, dict[str, Any]] = field(default_factory=dict)
    config: MCPServerConfig | None = None
    sensitive_values: list[str] = field(default_factory=list, repr=False)


@dataclass(slots=True)
class _AuthorizationLease:
    """Hold database row locks while one approved remote call is dispatched."""

    tool: _ToolSnapshot
    release: threading.Event
    worker: asyncio.Task[None]


class MCPRuntime:
    """Lazily run isolated MCP clients for persisted user connections."""

    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        config_validator: MCPConnectionConfigValidator | None = None,
        credential_encryption_service: CredentialEncryptionService | None = None,
        manager_factory: ManagerFactory = MCPClientManager,
        disconnect_timeout_seconds: float = DEFAULT_DISCONNECT_TIMEOUT_SECONDS,
        shutdown_timeout_seconds: float = DEFAULT_SHUTDOWN_TIMEOUT_SECONDS,
        remote_http_egress_protected: bool = False,
    ) -> None:
        """Store factories only; constructing the runtime starts no connection."""
        self._session_factory = session_factory
        self._config_validator = (
            config_validator or MCPConnectionConfigValidator()
        )
        self._credential_encryption_service = credential_encryption_service
        self._manager_factory = manager_factory
        self._disconnect_timeout_seconds = disconnect_timeout_seconds
        self._shutdown_timeout_seconds = shutdown_timeout_seconds
        self._remote_http_egress_protected = remote_http_egress_protected
        self._entries: dict[RuntimeKey, _RuntimeEntry] = {}
        self._locks: dict[RuntimeKey, asyncio.Lock] = {}
        # This set remains authoritative even if an entry cannot be removed.
        # A task leaves it only after asyncio confirms that the task is done.
        self._owner_tasks: set[asyncio.Task[None]] = set()
        self._closing = False

    def _assert_accepting_work(self) -> None:
        """Reject every new public operation as soon as shutdown begins."""
        if self._closing:
            raise MCPRuntimeError(
                "runtime_stopped",
                "The MCP runtime is shutting down.",
            )

    def _lock_for(self, key: RuntimeKey) -> asyncio.Lock:
        """Return one lock that serializes startup, calls, and disconnects."""
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    def _get_encryption_service(self) -> CredentialEncryptionService:
        """Create credential decryption support only when a secret is needed."""
        if self._credential_encryption_service is None:
            self._credential_encryption_service = CredentialEncryptionService()
        return self._credential_encryption_service

    @staticmethod
    def _fingerprint_connection(
        *,
        validated: ValidatedMCPConnectionConfig,
        auth_type: str,
        encrypted_credentials: str | None,
        timeout_seconds: float,
    ) -> str:
        """Hash every setting whose change requires a fresh live client."""
        encoded = json.dumps(
            {
                "transport": validated.transport,
                "server_url": validated.server_url,
                "stdio_template_code": validated.stdio_template_code,
                "configuration": validated.configuration,
                "auth_type": auth_type,
                "encrypted_credentials": encrypted_credentials,
                "timeout_seconds": timeout_seconds,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _schema_hash(schema: Mapping[str, Any]) -> str:
        """Hash discovery JSON exactly as the persistence service does."""
        encoded = json.dumps(
            schema,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _read_connection_snapshot(
        self,
        *,
        user_id: UUID,
        connection_id: UUID,
    ) -> _ConnectionSnapshot:
        """Recheck ownership, enabled state, and safe transport configuration."""
        db = self._session_factory()
        try:
            connection = MCPConnectionRepository(db).get_by_id(
                user_id=user_id,
                connection_id=connection_id,
            )
            if connection is None:
                raise MCPRuntimeError(
                    "connection_not_found",
                    "MCP connection not found.",
                )
            if not connection.is_enabled:
                raise MCPRuntimeError(
                    "connection_disabled",
                    "MCP connection is disabled.",
                )

            try:
                validated = self._config_validator.validate(
                    transport=connection.transport,
                    server_url=connection.server_url,
                    stdio_template_code=connection.stdio_template_code,
                    configuration=connection.configuration,
                )
            except (TypeError, ValueError) as exc:
                raise MCPRuntimeError(
                    "configuration_invalid",
                    "MCP connection configuration is invalid.",
                ) from None

            fingerprint = self._fingerprint_connection(
                validated=validated,
                auth_type=connection.auth_type,
                encrypted_credentials=connection.encrypted_credentials,
                timeout_seconds=float(connection.timeout_seconds),
            )
            return _ConnectionSnapshot(
                user_id=user_id,
                connection_id=connection_id,
                name=connection.name,
                validated=validated,
                auth_type=connection.auth_type,
                encrypted_credentials=connection.encrypted_credentials,
                timeout_seconds=float(connection.timeout_seconds),
                fingerprint=fingerprint,
            )
        finally:
            db.close()

    def _read_tool_snapshot(
        self,
        *,
        user_id: UUID,
        connection_id: UUID,
        tool_id: UUID,
    ) -> _ToolSnapshot:
        """Recheck ownership, availability, and explicit tool approval."""
        db = self._session_factory()
        try:
            tool = MCPConnectionToolRepository(db).get_by_id(
                user_id=user_id,
                connection_id=connection_id,
                tool_id=tool_id,
            )
            if tool is None:
                raise MCPRuntimeError("tool_not_found", "MCP tool not found.")
            if not tool.is_available or not tool.is_enabled:
                raise MCPRuntimeError("tool_disabled", "MCP tool is disabled.")
            return _ToolSnapshot(
                id=tool.id,
                remote_name=tool.remote_name,
                schema_hash=tool.schema_hash,
            )
        finally:
            db.close()

    def _decrypt_headers(self, snapshot: _ConnectionSnapshot) -> dict[str, str]:
        """Decrypt a supported HTTP credential directly into runtime headers."""
        if snapshot.auth_type == "none":
            if snapshot.encrypted_credentials is not None:
                raise MCPRuntimeError(
                    "credentials_invalid",
                    "MCP credentials are invalid.",
                )
            return {}
        if snapshot.validated.transport != "streamable_http":
            raise MCPRuntimeError(
                "credentials_invalid",
                "MCP credentials are invalid.",
            )
        if not snapshot.encrypted_credentials:
            raise MCPRuntimeError(
                "credentials_invalid",
                "MCP credentials are invalid.",
            )

        try:
            plaintext = self._get_encryption_service().decrypt(
                snapshot.encrypted_credentials
            )
            credentials = json.loads(plaintext)
        except Exception:
            raise MCPRuntimeError(
                "credentials_invalid",
                "MCP credentials could not be loaded.",
            ) from None
        finally:
            plaintext = None

        if not isinstance(credentials, dict):
            raise MCPRuntimeError(
                "credentials_invalid",
                "MCP credentials are invalid.",
            )
        if snapshot.auth_type == "bearer":
            token = credentials.get("token")
            if set(credentials) != {"token"} or not isinstance(token, str) or not token:
                raise MCPRuntimeError(
                    "credentials_invalid",
                    "MCP credentials are invalid.",
                )
            return {"Authorization": f"Bearer {token}"}
        if snapshot.auth_type == "api_key_header":
            header_name = credentials.get("header_name")
            api_key = credentials.get("api_key")
            if (
                set(credentials) != {"header_name", "api_key"}
                or header_name not in {"api-key", "x-api-key"}
                or not isinstance(api_key, str)
                or not api_key
            ):
                raise MCPRuntimeError(
                    "credentials_invalid",
                    "MCP credentials are invalid.",
                )
            return {header_name: api_key}
        raise MCPRuntimeError(
            "credentials_invalid",
            "MCP credentials are invalid.",
        )

    def _build_server_config(
        self,
        snapshot: _ConnectionSnapshot,
    ) -> MCPServerConfig:
        """Convert validated persistence fields into an SDK runtime target."""
        runtime_name = str(snapshot.connection_id)
        if snapshot.validated.transport == "stdio":
            template_code = snapshot.validated.stdio_template_code
            template = self._config_validator.stdio_templates.get(
                template_code or ""
            )
            if template is None:
                raise MCPRuntimeError(
                    "configuration_invalid",
                    "The approved MCP stdio template is unavailable.",
                )
            if snapshot.validated.configuration:
                raise MCPRuntimeError(
                    "configuration_invalid",
                    "This MCP stdio template does not support runtime options.",
                )
            return MCPServerConfig(
                name=runtime_name,
                transport="stdio",
                command=template.command,
                args=template.fixed_args,
                env=dict(template.fixed_environment),
                timeout_seconds=snapshot.timeout_seconds,
            )

        if not self._remote_http_egress_protected:
            raise MCPRuntimeError(
                "remote_http_disabled",
                "Remote MCP HTTP connections are disabled by deployment policy.",
            )
        assert snapshot.validated.server_url is not None
        return MCPServerConfig(
            name=runtime_name,
            transport="streamable_http",
            url=snapshot.validated.server_url,
            headers=self._decrypt_headers(snapshot),
            timeout_seconds=snapshot.timeout_seconds,
        )

    @staticmethod
    def _known_secrets(config: MCPServerConfig) -> list[str]:
        """Collect exact credential forms that must never leave the runtime."""
        secrets: list[str] = []
        for value in config.headers.values():
            if value:
                secrets.append(value)
            if value.lower().startswith("bearer ") and value[7:]:
                secrets.append(value[7:])
        return secrets

    @staticmethod
    def _redact_discovery_metadata(
        tools: list[dict[str, Any]],
        secrets: list[str],
    ) -> list[dict[str, Any]]:
        """Remove reflected credentials before discovery reaches persistence."""
        redacted = redact_json_value(tools, secrets)
        if not isinstance(redacted, list):
            raise MCPRuntimeError(
                "discovery_invalid",
                "MCP tool discovery returned an invalid response.",
            )
        for original, safe_tool in zip(tools, redacted):
            if not isinstance(safe_tool, dict):
                raise MCPRuntimeError(
                    "discovery_invalid",
                    "MCP tool discovery returned an invalid response.",
                )
            # A tool name is needed for later remote invocation. If the name
            # itself contains a credential, changing it would create a tool
            # that cannot be called, so reject that discovery response.
            if safe_tool.get("name") != original.get("name"):
                raise MCPRuntimeError(
                    "discovery_invalid",
                    "MCP tool discovery returned unsafe metadata.",
                )
        return redacted

    @staticmethod
    def _normalize_discovery(
        tools: list[dict[str, Any]],
    ) -> list[DiscoveredMCPTool]:
        """Convert manager metadata into the persistence service input shape."""
        return [
            DiscoveredMCPTool(
                name=tool["name"],
                description=tool.get("description"),
                input_schema=tool["input_schema"],
                annotations=tool.get("annotations"),
            )
            for tool in tools
        ]

    def _synchronize_discovery(
        self,
        *,
        snapshot: _ConnectionSnapshot,
        tools: list[dict[str, Any]],
    ) -> list[MCPToolDetails]:
        """Persist discovery and revoke approval for new or changed schemas."""
        db = self._session_factory()
        try:
            service = MCPConnectionService(
                db,
                credential_encryption_service=(
                    self._credential_encryption_service
                ),
                config_validator=self._config_validator,
            )
            synchronized = service.synchronize_discovered_tools(
                user_id=snapshot.user_id,
                connection_id=snapshot.connection_id,
                discovered_tools=self._normalize_discovery(tools),
            )
            db.commit()
            return synchronized
        except MCPRuntimeError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise MCPRuntimeError(
                "discovery_invalid",
                "MCP tool discovery could not be saved.",
            ) from None
        finally:
            db.close()

    @asynccontextmanager
    async def _authorization_lease(
        self,
        *,
        snapshot: _ConnectionSnapshot,
        tool_id: UUID,
        expected_schema_hash: str,
    ) -> AsyncIterator[_ToolSnapshot]:
        """Revalidate and lock connection/tool rows through remote dispatch.

        PostgreSQL row locks coordinate normal mutations across processes and
        workers. A mutation that disables or changes these rows waits for an
        already-authorized call to finish, while every later call sees the new
        values. Direct database administration and external systems that do
        not use these rows remain outside this application-level guarantee.
        """
        loop = asyncio.get_running_loop()
        ready: asyncio.Future[_ToolSnapshot] = loop.create_future()
        release = threading.Event()

        def publish_result(value: _ToolSnapshot) -> None:
            if not ready.done():
                ready.set_result(value)

        def publish_error(error: MCPRuntimeError) -> None:
            if not ready.done():
                ready.set_exception(error)

        def hold_rows() -> None:
            db = self._session_factory()
            try:
                connection = db.scalar(
                    select(MCPConnection)
                    .where(
                        MCPConnection.id == snapshot.connection_id,
                        MCPConnection.user_id == snapshot.user_id,
                    )
                    .with_for_update()
                )
                if connection is None:
                    raise MCPRuntimeError(
                        "connection_not_found",
                        "MCP connection not found.",
                    )
                if not connection.is_enabled:
                    raise MCPRuntimeError(
                        "connection_disabled",
                        "MCP connection is disabled.",
                    )
                try:
                    validated = self._config_validator.validate(
                        transport=connection.transport,
                        server_url=connection.server_url,
                        stdio_template_code=connection.stdio_template_code,
                        configuration=connection.configuration,
                    )
                except (TypeError, ValueError):
                    raise MCPRuntimeError(
                        "configuration_invalid",
                        "MCP connection configuration is invalid.",
                    ) from None
                fingerprint = self._fingerprint_connection(
                    validated=validated,
                    auth_type=connection.auth_type,
                    encrypted_credentials=connection.encrypted_credentials,
                    timeout_seconds=float(connection.timeout_seconds),
                )
                if fingerprint != snapshot.fingerprint:
                    raise MCPRuntimeError(
                        "configuration_changed",
                        "MCP connection configuration changed; retry the call.",
                    )

                tool = db.scalar(
                    select(MCPConnectionTool)
                    .where(
                        MCPConnectionTool.id == tool_id,
                        MCPConnectionTool.connection_id == snapshot.connection_id,
                    )
                    .with_for_update()
                )
                if tool is None:
                    raise MCPRuntimeError("tool_not_found", "MCP tool not found.")
                if not tool.is_available or not tool.is_enabled:
                    raise MCPRuntimeError("tool_disabled", "MCP tool is disabled.")
                if tool.schema_hash != expected_schema_hash:
                    raise MCPRuntimeError(
                        "tool_schema_changed",
                        "MCP tool approval no longer matches its current schema.",
                    )
                loop.call_soon_threadsafe(
                    publish_result,
                    _ToolSnapshot(
                        id=tool.id,
                        remote_name=tool.remote_name,
                        schema_hash=tool.schema_hash,
                    ),
                )
                release.wait()
            except MCPRuntimeError as exc:
                loop.call_soon_threadsafe(publish_error, exc)
            except Exception:
                loop.call_soon_threadsafe(
                    publish_error,
                    MCPRuntimeError(
                        "authorization_failed",
                        "MCP authorization could not be verified.",
                    ),
                )
            finally:
                db.rollback()
                db.close()

        worker = asyncio.create_task(
            asyncio.to_thread(hold_rows),
            name=f"mcp-authorization-{snapshot.connection_id}",
        )
        try:
            authorized_tool = await asyncio.wait_for(
                asyncio.shield(ready),
                timeout=snapshot.timeout_seconds,
            )
        except asyncio.TimeoutError:
            release.set()
            await asyncio.wait(
                {worker},
                timeout=self._disconnect_timeout_seconds,
            )
            raise MCPRuntimeError(
                "authorization_timeout",
                "MCP authorization timed out.",
            ) from None
        except BaseException:
            release.set()
            await asyncio.wait(
                {worker},
                timeout=self._disconnect_timeout_seconds,
            )
            raise
        lease = _AuthorizationLease(
            tool=authorized_tool,
            release=release,
            worker=worker,
        )
        try:
            yield lease.tool
        finally:
            lease.release.set()
            await asyncio.wait(
                {lease.worker},
                timeout=self._disconnect_timeout_seconds,
            )

    async def _connection_owner(
        self,
        *,
        entry: _RuntimeEntry,
        config: MCPServerConfig,
        timeout_seconds: float,
    ) -> None:
        """Open, use, and close one SDK client entirely inside this task."""
        server_name = config.name
        manager: MCPClientManager | None = None
        installed_log_filter = install_sdk_secret_log_filter(
            entry.sensitive_values
        )
        failure: MCPRuntimeError | None = None
        stop_future: asyncio.Future[Any] | None = None
        active_command: _OwnerCommand | None = None
        try:
            manager = self._manager_factory([config])
            # Do not wrap client entry in an AnyIO cancel scope. MCP 2.3.0
            # keeps transport scopes open for the whole session, so an outer
            # scope cannot exit until the client closes. The caller enforces
            # the connect timeout by cancelling this owner task instead.
            await manager.connect(server_name)
            discovered = await manager.discover_tools(server_name)
            discovered = self._redact_discovery_metadata(
                discovered,
                entry.sensitive_values,
            )
            entry.tools = {tool["name"]: tool for tool in discovered}
            entry.state = "connected"
            if not entry.ready.done():
                entry.ready.set_result(discovered)

            while True:
                command = await entry.queue.get()
                if command.operation == "stop":
                    entry.state = "stopping"
                    stop_future = command.future
                    break
                active_command = command
                try:
                    with anyio.fail_after(command.timeout_seconds):
                        if command.operation == "discover":
                            result = await manager.discover_tools(server_name)
                            result = self._redact_discovery_metadata(
                                result,
                                entry.sensitive_values,
                            )
                            entry.tools = {
                                tool["name"]: tool for tool in result
                            }
                        else:
                            assert command.tool_name is not None
                            result = await manager.call_tool(
                                server_name=server_name,
                                tool_name=command.tool_name,
                                arguments=command.arguments,
                            )
                except TimeoutError:
                    failure = MCPRuntimeError(
                        "operation_timeout",
                        "The MCP operation timed out.",
                    )
                    self._set_future_exception(
                        command.future,
                        failure,
                    )
                    # A timed-out protocol operation can leave the stream in an
                    # unknown state. Close this client instead of reusing it.
                    break
                except Exception:
                    self._set_future_exception(
                        command.future,
                        MCPRuntimeError(
                            "operation_failed",
                            "The MCP operation failed.",
                        ),
                    )
                else:
                    if command.operation == "call":
                        result = redact_mcp_tool_result(
                            result,
                            entry.sensitive_values,
                        )
                    if not command.future.done():
                        command.future.set_result(result)
                finally:
                    if command.future.done():
                        active_command = None
        except TimeoutError:
            failure = MCPRuntimeError(
                "connection_timeout",
                "The MCP connection timed out.",
            )
        except asyncio.CancelledError:
            failure = MCPRuntimeError(
                "runtime_stopped",
                "The MCP runtime stopped.",
            )
        except Exception:
            failure = MCPRuntimeError(
                "connection_failed",
                "The MCP connection could not be started.",
            )
        finally:
            if failure is not None and not entry.ready.done():
                entry.ready.set_exception(failure)
            if active_command is not None:
                self._set_future_exception(
                    active_command.future,
                    failure
                    or MCPRuntimeError(
                        "runtime_stopped",
                        "The MCP runtime stopped.",
                    ),
                )
            self._fail_pending_commands(entry, failure)

            cleanup_error: MCPRuntimeError | None = None
            if manager is not None:
                try:
                    # Cleanup is deliberately unwrapped: the caller's bounded
                    # wait cancels this owner if a manager cannot close in time.
                    await manager.disconnect_all()
                except BaseException:
                    cleanup_error = MCPRuntimeError(
                        "disconnect_timeout",
                        "The MCP connection did not close cleanly.",
                    )

            config.headers.clear()
            entry.sensitive_values.clear()
            remove_sdk_secret_log_filter(installed_log_filter)
            entry.tools.clear()
            entry.closed.set()
            if stop_future is not None:
                if cleanup_error is not None:
                    self._set_future_exception(stop_future, cleanup_error)
                elif not stop_future.done():
                    stop_future.set_result(None)
            self._resolve_queued_commands(entry, cleanup_error)

    @staticmethod
    def _set_future_exception(
        future: asyncio.Future[Any],
        error: MCPRuntimeError,
    ) -> None:
        """Complete one waiting caller with a safe runtime exception."""
        if not future.done():
            future.set_exception(error)

    def _fail_pending_commands(
        self,
        entry: _RuntimeEntry,
        failure: MCPRuntimeError | None,
    ) -> None:
        """Release queued callers when their owner task can no longer serve them."""
        while not entry.queue.empty():
            command = entry.queue.get_nowait()
            if command.operation == "stop":
                entry.queue.put_nowait(command)
                break
            self._set_future_exception(
                command.future,
                failure
                or MCPRuntimeError(
                    "runtime_stopped",
                    "The MCP runtime stopped.",
                ),
            )

    @staticmethod
    def _resolve_queued_commands(
        entry: _RuntimeEntry,
        cleanup_error: MCPRuntimeError | None,
    ) -> None:
        """Release commands that were queued while the connection was closing."""
        while not entry.queue.empty():
            command = entry.queue.get_nowait()
            error = cleanup_error or MCPRuntimeError(
                "runtime_stopped",
                "The MCP runtime stopped.",
            )
            if not command.future.done():
                command.future.set_exception(error)

    async def _send_command(
        self,
        *,
        entry: _RuntimeEntry,
        operation: Literal["discover", "call", "stop"],
        timeout_seconds: float,
        tool_name: str | None = None,
        arguments: Mapping[str, Any] | None = None,
    ) -> Any:
        """Queue one bounded operation for the connection's SDK owner task."""
        future = asyncio.get_running_loop().create_future()
        await entry.queue.put(
            _OwnerCommand(
                operation=operation,
                future=future,
                timeout_seconds=timeout_seconds,
                tool_name=tool_name,
                arguments=dict(arguments or {}),
            )
        )
        try:
            return await asyncio.wait_for(
                asyncio.shield(future),
                timeout=timeout_seconds + self._disconnect_timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise MCPRuntimeError(
                "operation_timeout",
                "The MCP operation timed out.",
            ) from None

    @staticmethod
    async def _wait_for_owner(
        task: asyncio.Task[None],
        timeout_seconds: float,
    ) -> bool:
        """Wait by wall clock and return whether asyncio confirmed termination."""
        done, _pending = await asyncio.wait({task}, timeout=timeout_seconds)
        return bool(done)

    async def _stop_entry_locked(self, entry: _RuntimeEntry) -> bool:
        """Ask one owner to close, then cancel it if cooperative stop expires."""
        task = entry.task
        if task is None or task.done():
            return True
        if entry.state != "starting":
            entry.state = "stopping"
            future = asyncio.get_running_loop().create_future()
            future.add_done_callback(
                lambda completed: (
                    completed.exception()
                    if not completed.cancelled()
                    else None
                )
            )
            await entry.queue.put(
                _OwnerCommand(
                    operation="stop",
                    future=future,
                    timeout_seconds=self._disconnect_timeout_seconds,
                )
            )
            if await self._wait_for_owner(
                task,
                self._disconnect_timeout_seconds,
            ):
                return True

        task.cancel()
        return await self._wait_for_owner(
            task,
            self._disconnect_timeout_seconds,
        )

    async def _cancel_entry_locked(self, entry: _RuntimeEntry) -> bool:
        """Cancel one owner and report whether same-task cleanup really ended."""
        task = entry.task
        if task is None or task.done():
            return True
        task.cancel()
        return await self._wait_for_owner(
            task,
            self._disconnect_timeout_seconds,
        )

    def _track_owner_task(self, task: asyncio.Task[None]) -> None:
        """Keep each owner discoverable until its task is actually finished."""
        self._owner_tasks.add(task)

        def remove_finished(finished: asyncio.Task[None]) -> None:
            self._owner_tasks.discard(finished)

        task.add_done_callback(remove_finished)

    async def _ensure_connected_locked(
        self,
        snapshot: _ConnectionSnapshot,
    ) -> tuple[_RuntimeEntry, list[dict[str, Any]] | None]:
        """Reuse matching live state or start exactly one owner task."""
        self._assert_accepting_work()
        key = (snapshot.user_id, snapshot.connection_id)
        current = self._entries.get(key)
        if current is not None and (
            current.task is None
            or current.task.done()
            or current.fingerprint != snapshot.fingerprint
        ):
            stopped = await self._stop_entry_locked(current)
            if not stopped:
                raise MCPRuntimeError(
                    "disconnect_incomplete",
                    "The previous MCP runtime did not stop; retry later.",
                )
            if self._entries.get(key) is current:
                self._entries.pop(key, None)
            current = None
        if current is not None:
            return current, None

        config = self._build_server_config(snapshot)
        loop = asyncio.get_running_loop()
        entry = _RuntimeEntry(
            key=key,
            fingerprint=snapshot.fingerprint,
            queue=asyncio.Queue(),
            ready=loop.create_future(),
            closed=asyncio.Event(),
            config=config,
            sensitive_values=self._known_secrets(config),
        )
        entry.task = asyncio.create_task(
            self._connection_owner(
                entry=entry,
                config=config,
                timeout_seconds=snapshot.timeout_seconds,
            ),
            name=f"mcp-owner-{snapshot.connection_id}",
        )
        self._track_owner_task(entry.task)
        self._entries[key] = entry
        try:
            discovered = await asyncio.wait_for(
                asyncio.shield(entry.ready),
                timeout=snapshot.timeout_seconds,
            )
        except (asyncio.TimeoutError, MCPRuntimeError) as exc:
            if isinstance(exc, asyncio.TimeoutError):
                stopped = await self._cancel_entry_locked(entry)
            else:
                stopped = await self._stop_entry_locked(entry)
            if stopped and self._entries.get(key) is entry:
                self._entries.pop(key, None)
            if not stopped:
                raise MCPRuntimeError(
                    "disconnect_incomplete",
                    "The failed MCP runtime did not stop cleanly.",
                ) from None
            if isinstance(exc, MCPRuntimeError):
                raise
            if entry.ready.done() and not entry.ready.cancelled():
                ready_error = entry.ready.exception()
                if isinstance(ready_error, MCPRuntimeError):
                    raise ready_error
            raise MCPRuntimeError(
                "connection_timeout",
                "The MCP connection timed out.",
            ) from None
        return entry, discovered

    async def _authorized_snapshot_locked(
        self,
        *,
        user_id: UUID,
        connection_id: UUID,
    ) -> _ConnectionSnapshot:
        """Read current authorization and stop stale local state on rejection."""
        self._assert_accepting_work()
        key = (user_id, connection_id)
        try:
            return await asyncio.to_thread(
                self._read_connection_snapshot,
                user_id=user_id,
                connection_id=connection_id,
            )
        except MCPRuntimeError:
            entry = self._entries.get(key)
            if entry is not None:
                stopped = await self._stop_entry_locked(entry)
                if stopped and self._entries.get(key) is entry:
                    self._entries.pop(key, None)
            raise

    async def connect(
        self,
        *,
        user_id: UUID,
        connection_id: UUID,
    ) -> MCPRuntimeStatus:
        """Lazily open one owned enabled connection and persist discovery."""
        self._assert_accepting_work()
        key = (user_id, connection_id)
        async with self._lock_for(key):
            snapshot = await self._authorized_snapshot_locked(
                user_id=user_id,
                connection_id=connection_id,
            )
            entry, discovered = await self._ensure_connected_locked(snapshot)
            if discovered is not None:
                try:
                    await asyncio.to_thread(
                        self._synchronize_discovery,
                        snapshot=snapshot,
                        tools=discovered,
                    )
                except MCPRuntimeError:
                    stopped = await self._stop_entry_locked(entry)
                    if stopped and self._entries.get(key) is entry:
                        self._entries.pop(key, None)
                    raise
            return MCPRuntimeStatus(
                user_id=user_id,
                connection_id=connection_id,
                state="connected",
                tool_count=len(entry.tools),
            )

    async def call_tool(
        self,
        *,
        user_id: UUID,
        connection_id: UUID,
        tool_id: UUID,
        arguments: Mapping[str, Any] | None = None,
    ) -> Any:
        """Reauthorize, refresh discovery, then call one explicitly enabled tool."""
        self._assert_accepting_work()
        key = (user_id, connection_id)
        async with self._lock_for(key):
            snapshot = await self._authorized_snapshot_locked(
                user_id=user_id,
                connection_id=connection_id,
            )
            await asyncio.to_thread(
                self._read_tool_snapshot,
                user_id=user_id,
                connection_id=connection_id,
                tool_id=tool_id,
            )
            entry, initial_discovery = await self._ensure_connected_locked(
                snapshot
            )
            discovered = initial_discovery
            if discovered is None:
                discovered = await self._send_command(
                    entry=entry,
                    operation="discover",
                    timeout_seconds=snapshot.timeout_seconds,
                )
            await asyncio.to_thread(
                self._synchronize_discovery,
                snapshot=snapshot,
                tools=discovered,
            )

            # Discovery may have changed the schema and revoked approval, so
            # authorization is deliberately repeated immediately before use.
            tool = await asyncio.to_thread(
                self._read_tool_snapshot,
                user_id=user_id,
                connection_id=connection_id,
                tool_id=tool_id,
            )
            live_tool = entry.tools.get(tool.remote_name)
            if live_tool is None:
                raise MCPRuntimeError("tool_disabled", "MCP tool is disabled.")
            expected_schema_hash = self._schema_hash(
                live_tool["input_schema"]
            )

            # The final database check happens directly around queue dispatch.
            # PostgreSQL locks prevent cooperating mutation transactions from
            # committing until this invocation finishes or is cancelled.
            async with self._authorization_lease(
                snapshot=snapshot,
                tool_id=tool_id,
                expected_schema_hash=expected_schema_hash,
            ) as authorized_tool:
                self._assert_accepting_work()
                if authorized_tool.remote_name != tool.remote_name:
                    raise MCPRuntimeError(
                        "tool_changed",
                        "MCP tool metadata changed; retry the call.",
                    )
                try:
                    return await self._send_command(
                        entry=entry,
                        operation="call",
                        timeout_seconds=snapshot.timeout_seconds,
                        tool_name=authorized_tool.remote_name,
                        arguments=arguments,
                    )
                except MCPRuntimeError as exc:
                    if exc.code == "operation_timeout":
                        stopped = await self._cancel_entry_locked(entry)
                        if stopped and self._entries.get(key) is entry:
                            self._entries.pop(key, None)
                    raise

    async def refresh_tools(
        self,
        *,
        user_id: UUID,
        connection_id: UUID,
    ) -> list[MCPToolDetails]:
        """Explicitly rediscover and persist tools for one enabled connection."""
        self._assert_accepting_work()
        key = (user_id, connection_id)
        async with self._lock_for(key):
            snapshot = await self._authorized_snapshot_locked(
                user_id=user_id,
                connection_id=connection_id,
            )
            entry, initial_discovery = await self._ensure_connected_locked(
                snapshot
            )
            discovered = initial_discovery
            if discovered is None:
                discovered = await self._send_command(
                    entry=entry,
                    operation="discover",
                    timeout_seconds=snapshot.timeout_seconds,
                )
            return await asyncio.to_thread(
                self._synchronize_discovery,
                snapshot=snapshot,
                tools=discovered,
            )

    async def disconnect(
        self,
        *,
        user_id: UUID,
        connection_id: UUID,
    ) -> MCPRuntimeStatus:
        """Close only the live runtime identified by both owner and connection."""
        key = (user_id, connection_id)
        async with self._lock_for(key):
            entry = self._entries.get(key)
            if entry is not None:
                stopped = await self._stop_entry_locked(entry)
                if not stopped:
                    raise MCPRuntimeError(
                        "disconnect_incomplete",
                        "The MCP connection is still stopping.",
                    )
                if self._entries.get(key) is entry:
                    self._entries.pop(key, None)
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
    ) -> MCPRuntimeStatus:
        """Disconnect local state after an in-process persistence mutation.

        Future management services should call this after a successful commit.
        Changes from another worker are still enforced by database revalidation
        before every operation; their idle socket closes on its next local use
        unless deployment messaging requests earlier invalidation.
        """
        return await self.disconnect(
            user_id=user_id,
            connection_id=connection_id,
        )

    def status(
        self,
        *,
        user_id: UUID,
        connection_id: UUID,
    ) -> MCPRuntimeStatus:
        """Report only live in-process state, never the persisted status column."""
        key = (user_id, connection_id)
        entry = self._entries.get(key)
        if entry is None or entry.task is None or entry.task.done():
            return MCPRuntimeStatus(
                user_id=user_id,
                connection_id=connection_id,
                state="disconnected",
            )
        return MCPRuntimeStatus(
            user_id=user_id,
            connection_id=connection_id,
            state=entry.state,
            tool_count=len(entry.tools),
        )

    async def shutdown(self) -> None:
        """Stop owners by a wall-clock deadline or report every survivor."""
        self._closing = True
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._shutdown_timeout_seconds

        # Ask idle owners to stop without waiting on per-connection locks. An
        # active call will either finish first or receive cancellation below.
        for entry in list(self._entries.values()):
            task = entry.task
            if task is None or task.done() or entry.state == "starting":
                continue
            entry.state = "stopping"
            future = loop.create_future()
            future.add_done_callback(
                lambda completed: (
                    completed.exception()
                    if not completed.cancelled()
                    else None
                )
            )
            entry.queue.put_nowait(
                _OwnerCommand(
                    operation="stop",
                    future=future,
                    timeout_seconds=self._disconnect_timeout_seconds,
                )
            )

        owners = {task for task in self._owner_tasks if not task.done()}
        graceful_budget = min(
            self._disconnect_timeout_seconds,
            max(0.0, self._shutdown_timeout_seconds / 2),
        )
        if owners and graceful_budget:
            await asyncio.wait(owners, timeout=graceful_budget)

        survivors = {task for task in self._owner_tasks if not task.done()}
        for task in survivors:
            task.cancel()

        remaining_budget = max(0.0, deadline - loop.time())
        if survivors and remaining_budget:
            await asyncio.wait(survivors, timeout=remaining_budget)

        survivors = {task for task in self._owner_tasks if not task.done()}
        if survivors:
            # Remove the easiest in-memory copies of credentials even when a
            # broken manager refuses cancellation. The surviving task remains
            # registered so a later shutdown attempt can still control it.
            for entry in self._entries.values():
                if entry.config is not None:
                    entry.config.headers.clear()
                entry.sensitive_values.clear()
            raise MCPShutdownError(len(survivors))

        self._entries.clear()
        self._locks.clear()
