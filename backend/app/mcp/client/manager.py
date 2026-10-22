
"""Manage connections and tool calls for multiple MCP servers.

``MCPToolProvider`` asks this manager which servers exist, connects to allowed
servers, and discovers their tools. ``MCPToolAdapter`` calls the manager when
the LangGraph Tool Node executes a selected remote tool.
"""

from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

from mcp import Client

from app.mcp.config.server_config import MCPServerConfig
from app.mcp.security.redaction import redact_mcp_tool_result


@dataclass
class _ServerConnection:
    """Keep the live SDK client, cleanup stack, and discovered tools together."""

    # Original settings used to open this connection.
    config: MCPServerConfig
    # Live SDK client that sends MCP requests.
    client: Client
    # Owns async cleanup callbacks so transports close correctly.
    exit_stack: AsyncExitStack
    # Latest discovered SDK tool objects, indexed by their remote name.
    tools: dict[str, Any] = field(default_factory=dict)


class MCPClientManager:
    """Own and reuse async connections to all configured MCP servers."""

    def __init__(
        self,
        server_configs: list[MCPServerConfig],
    ) -> None:
        """Index server configs by unique name and start with no connections."""
        # Configuration is stable; connection state changes as servers open/close.
        self._configs: dict[str, MCPServerConfig] = {}

        for config in server_configs:
            if config.name in self._configs:
                raise ValueError(
                    f"Duplicate MCP server name: {config.name}"
                )

            self._configs[config.name] = config

        self._connections: dict[str, _ServerConnection] = {}

    def _get_config(self, server_name: str) -> MCPServerConfig:
        """Return configured settings or raise for an unknown server name."""
        config = self._configs.get(server_name)

        if config is None:
            raise KeyError(
                f"MCP server is not configured: {server_name}"
            )

        return config

    def _get_connection(
        self,
        server_name: str,
    ) -> _ServerConnection:
        """Return a live connection or raise when the server is not connected."""
        connection = self._connections.get(server_name)

        if connection is None:
            raise RuntimeError(
                f"MCP server is not connected: {server_name}"
            )

        return connection

    async def connect(self, server_name: str) -> dict[str, Any]:
        """Open one server once, discover its tools, and return connection status."""

        config = self._get_config(server_name)

        # Make connect() idempotent.
        if server_name in self._connections:
            return {
                "server": server_name,
                "status": "connected",
                "already_connected": True,
            }

        client = Client(config.build_client_target())
        exit_stack = AsyncExitStack()

        try:
            # Opens the transport and initializes the MCP client.
            await exit_stack.enter_async_context(client)

            connection = _ServerConnection(
                config=config,
                client=client,
                exit_stack=exit_stack,
            )
            self._connections[server_name] = connection

            # Verify the server can respond to tool discovery.
            tools = await self.discover_tools(server_name)

            return {
                "server": server_name,
                "status": "connected",
                "tool_count": len(tools),
            }

        except BaseException as exc:
            self._connections.pop(server_name, None)
            try:
                await exit_stack.aclose()
            except BaseException:
                # The caller receives one stable error below. Raw SDK cleanup
                # exceptions can contain request details and must not escape.
                pass

            # Cancellation must remain cancellation after same-task cleanup.
            if not isinstance(exc, Exception):
                raise

            # Do not copy provider exception text into an application error.
            # Some SDKs include request headers or URLs containing credentials.
            raise ConnectionError(
                f"Could not connect to MCP server '{server_name}'."
            ) from None

    async def disconnect(self, server_name: str) -> dict[str, Any]:
        """Close one server and clear its cached discovered tools."""

        connection = self._connections.pop(server_name, None)

        if connection is None:
            return {
                "server": server_name,
                "status": "disconnected",
                "was_connected": False,
            }

        try:
            await connection.exit_stack.aclose()
        finally:
            connection.tools.clear()

        return {
            "server": server_name,
            "status": "disconnected",
            "was_connected": True,
        }

    async def disconnect_all(self) -> None:
        """Close every active server and report if any cleanup failed."""

        errors: list[Exception] = []

        for server_name in list(self._connections):
            try:
                await self.disconnect(server_name)
            except Exception as exc:
                errors.append(exc)

        if errors:
            raise RuntimeError(
                f"{len(errors)} MCP connection(s) failed to close"
            ) from errors[0]

    def list_servers(self) -> list[dict[str, Any]]:
        """Return safe server names, transports, statuses, and tool counts."""

        servers = []

        for name, config in self._configs.items():
            connection = self._connections.get(name)

            servers.append(
                {
                    "name": name,
                    "transport": config.transport,
                    "status": (
                        "connected"
                        if connection is not None
                        else "disconnected"
                    ),
                    "tool_count": (
                        len(connection.tools)
                        if connection is not None
                        else 0
                    ),
                }
            )

        return servers

    async def discover_tools(
        self,
        server_name: str,
    ) -> list[dict[str, Any]]:
        """Refresh all paginated tools from one server and return plain metadata."""

        connection = self._get_connection(server_name)

        discovered: dict[str, Any] = {}
        cursor: str | None = None

        # Handle paginated tool listings.
        while True:
            page = await connection.client.list_tools(
                cursor=cursor,
                cache_mode="refresh",
            )

            for tool in page.tools:
                discovered[tool.name] = tool

            cursor = page.next_cursor

            if cursor is None:
                break

        connection.tools = discovered

        # Return plain metadata rather than SDK model instances.
        return [
            {
                "server": server_name,
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "annotations": _plain_annotations(
                    getattr(tool, "annotations", None)
                ),
            }
            for tool in discovered.values()
        ]

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Verify a remote tool exists, call it, and return its SDK result."""

        connection = self._get_connection(server_name)

        # Ensure the manager has discovered the server's tools.
        if tool_name not in connection.tools:
            await self.discover_tools(server_name)

        if tool_name not in connection.tools:
            raise KeyError(
                f"Tool '{tool_name}' is not exposed by "
                f"MCP server '{server_name}'"
            )

        result = await connection.client.call_tool(
            name=tool_name,
            arguments=arguments or {},
        )
        secrets: list[str] = []
        for value in connection.config.headers.values():
            if value:
                secrets.append(value)
            if value.lower().startswith("bearer ") and value[7:]:
                secrets.append(value[7:])
        return redact_mcp_tool_result(result, secrets)

    async def health_check(
        self,
        server_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Check whether one or all configured servers can answer discovery."""

        names = (
            [server_name]
            if server_name is not None
            else list(self._configs)
        )

        results = []

        for name in names:
            # Unknown names are configuration errors.
            self._get_config(name)
            connection = self._connections.get(name)

            if connection is None:
                results.append(
                    {
                        "server": name,
                        "healthy": False,
                        "status": "disconnected",
                    }
                )
                continue

            try:
                tools = await self.discover_tools(name)

                results.append(
                    {
                        "server": name,
                        "healthy": True,
                        "status": "connected",
                        "tool_count": len(tools),
                    }
                )

            except Exception:
                results.append(
                    {
                        "server": name,
                        "healthy": False,
                        "status": "error",
                        "error": "MCP health check failed.",
                    }
                )

        return results


def _plain_annotations(value: Any) -> dict[str, Any] | None:
    """Convert optional SDK annotation models into plain stored metadata."""
    if value is None:
        return None
    if isinstance(value, dict):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json", by_alias=True, exclude_none=True)
        return dumped if isinstance(dumped, dict) else None
    return None
