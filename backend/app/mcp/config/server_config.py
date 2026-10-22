"""Validated connection settings for one MCP server.

``MCPClientManager`` reads this object when opening a local stdio process or a
remote Streamable HTTP connection. Transport-specific fields are checked when
the object is created so invalid combinations fail early.
"""

from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlparse

from mcp import StdioServerParameters

from app.mcp.client.http_transport import (
    RestrictedStreamableHTTPTransport,
)


# The two transport types currently understood by the installed MCP SDK.
MCPTransport = Literal["stdio", "streamable_http"]


@dataclass(frozen=True)
class MCPServerConfig:
    """Store one server's name, transport, and transport-specific settings."""

    # Unique local name used for permissions, discovery, and public tool names.
    name: str
    # Selects local-process stdio or remote Streamable HTTP communication.
    transport: MCPTransport

    # Remote server address; used only by Streamable HTTP.
    url: str | None = None

    # Decrypted HTTP credentials exist only on the in-memory runtime config.
    # repr=False prevents an accidental object log from printing them.
    headers: dict[str, str] = field(default_factory=dict, repr=False)
    timeout_seconds: float = 30.0

    # Program, arguments, and environment used only for a local stdio server.
    command: str | None = None
    args: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Reject missing names and fields that do not match the transport."""
        if not self.name.strip():
            raise ValueError("MCP server name cannot be empty")

        if self.transport == "stdio":
            if not self.command or not self.command.strip():
                raise ValueError(
                    "A command is required for stdio transport"
                )

            if self.url is not None:
                raise ValueError(
                    "A stdio server must not specify a URL"
                )

        elif self.transport == "streamable_http":
            if not self.url:
                raise ValueError(
                    "A URL is required for Streamable HTTP"
                )

            parsed = urlparse(self.url)

            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(
                    "The MCP URL must be a valid HTTP or HTTPS URL"
                )

            if self.command is not None:
                raise ValueError(
                    "An HTTP server must not specify a command"
                )

        if self.timeout_seconds <= 0:
            raise ValueError("MCP timeout must be greater than zero")

    def build_client_target(
        self,
    ) -> StdioServerParameters | RestrictedStreamableHTTPTransport:
        """Return safe process or HTTP settings expected by the MCP SDK."""

        if self.transport == "streamable_http":
            assert self.url is not None
            return RestrictedStreamableHTTPTransport(
                url=self.url,
                headers=self.headers,
                timeout_seconds=self.timeout_seconds,
            )

        assert self.command is not None

        return StdioServerParameters(
            command=self.command,
            args=list(self.args),
            env=dict(self.env) or None,
        )
