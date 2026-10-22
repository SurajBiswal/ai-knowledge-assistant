"""Validate persisted MCP settings at the application's trust boundary.

The service calls this module before saving any user-supplied transport data.
Stdio users can select only an operator-approved template; they cannot submit a
command. Remote endpoints must use public HTTPS addresses and are resolved to
reject private or special-purpose networks.

DNS validation alone cannot prevent every SSRF technique. The runtime repeats
this validation and disables redirects and environment proxies, but arbitrary
remote HTTP connections remain gated until deployment-level egress controls
protect the actual socket destination. See ``app/mcp/SECURITY.md``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
import ipaddress
import json
import socket
from typing import Any
from urllib.parse import urlsplit

from app.mcp.config.stdio_templates import (
    ApprovedStdioServerTemplate,
    DEFAULT_STDIO_SERVER_TEMPLATES,
)


HostResolver = Callable[[str], Iterable[str]]

MAX_URL_CHARS = 2_048
MAX_CONFIGURATION_CHARS = 16_000
DEFAULT_HTTP_PORTS = frozenset({443})
SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
)


@dataclass(frozen=True, slots=True)
class ValidatedMCPConnectionConfig:
    """Return normalized safe fields that may be written to PostgreSQL."""

    transport: str
    server_url: str | None
    stdio_template_code: str | None
    configuration: dict[str, str | int | float | bool | None]


def _resolve_host_addresses(hostname: str) -> set[str]:
    """Resolve all current IP addresses for an HTTP endpoint hostname."""
    results = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    return {result[4][0] for result in results}


def _is_public_address(value: str) -> bool:
    """Return true only for globally routable IPv4 or IPv6 addresses."""
    try:
        return ipaddress.ip_address(value).is_global
    except ValueError:
        return False


def _validate_safe_configuration(
    configuration: Mapping[str, Any] | None,
    *,
    allowed_keys: frozenset[str],
) -> dict[str, str | int | float | bool | None]:
    """Allow only declared scalar options and reject secret-looking fields."""
    safe = dict(configuration or {})
    if any(not isinstance(key, str) for key in safe):
        raise ValueError("Stdio configuration option names must be strings.")
    unknown_keys = set(safe) - set(allowed_keys)
    if unknown_keys:
        names = ", ".join(sorted(unknown_keys))
        raise ValueError(f"Unsupported stdio configuration option(s): {names}.")

    for key, value in safe.items():
        normalized_key = key.strip().lower()
        if not normalized_key or any(
            part in normalized_key for part in SENSITIVE_KEY_PARTS
        ):
            raise ValueError(
                "Secrets are not allowed in general MCP configuration."
            )
        if not isinstance(value, (str, int, float, bool, type(None))):
            raise ValueError(
                "Stdio configuration values must be simple JSON values."
            )

    try:
        encoded = json.dumps(
            safe,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except ValueError as exc:
        raise ValueError(
            "Stdio configuration must contain finite JSON values."
        ) from exc
    if len(encoded) > MAX_CONFIGURATION_CHARS:
        raise ValueError("MCP configuration is too large.")
    return safe


class MCPConnectionConfigValidator:
    """Validate either an approved stdio template or a public HTTPS endpoint."""

    def __init__(
        self,
        *,
        stdio_templates: Mapping[
            str,
            ApprovedStdioServerTemplate,
        ] = DEFAULT_STDIO_SERVER_TEMPLATES,
        host_resolver: HostResolver = _resolve_host_addresses,
        allowed_http_ports: frozenset[int] = DEFAULT_HTTP_PORTS,
    ) -> None:
        """Store trusted templates, DNS resolver, and allowed remote ports."""
        self.stdio_templates = dict(stdio_templates)
        self.host_resolver = host_resolver
        self.allowed_http_ports = allowed_http_ports

    def validate(
        self,
        *,
        transport: str,
        server_url: str | None = None,
        stdio_template_code: str | None = None,
        configuration: Mapping[str, Any] | None = None,
    ) -> ValidatedMCPConnectionConfig:
        """Return safe normalized fields or raise a user-friendly error."""
        if transport == "stdio":
            return self._validate_stdio(
                server_url=server_url,
                template_code=stdio_template_code,
                configuration=configuration,
            )
        if transport == "streamable_http":
            return self._validate_http(
                server_url=server_url,
                template_code=stdio_template_code,
                configuration=configuration,
            )
        raise ValueError("Unsupported MCP transport.")

    def _validate_stdio(
        self,
        *,
        server_url: str | None,
        template_code: str | None,
        configuration: Mapping[str, Any] | None,
    ) -> ValidatedMCPConnectionConfig:
        """Require one known template and reject every remote URL field."""
        if server_url is not None:
            raise ValueError("A stdio MCP connection cannot specify a URL.")
        if not template_code or template_code not in self.stdio_templates:
            raise ValueError("Select an approved stdio server template.")

        template = self.stdio_templates[template_code]
        safe_configuration = _validate_safe_configuration(
            configuration,
            allowed_keys=template.allowed_configuration_keys,
        )
        return ValidatedMCPConnectionConfig(
            transport="stdio",
            server_url=None,
            stdio_template_code=template.code,
            configuration=safe_configuration,
        )

    def _validate_http(
        self,
        *,
        server_url: str | None,
        template_code: str | None,
        configuration: Mapping[str, Any] | None,
    ) -> ValidatedMCPConnectionConfig:
        """Require a resolvable public HTTPS endpoint with no URL credentials."""
        if template_code is not None:
            raise ValueError(
                "A Streamable HTTP connection cannot use a stdio template."
            )
        if configuration:
            raise ValueError(
                "Streamable HTTP settings must use explicit URL/auth fields."
            )
        if not server_url or not server_url.strip():
            raise ValueError("A Streamable HTTP URL is required.")

        normalized_url = server_url.strip()
        if len(normalized_url) > MAX_URL_CHARS:
            raise ValueError("The MCP server URL is too long.")

        parsed = urlsplit(normalized_url)
        if parsed.scheme.lower() != "https":
            raise ValueError("Streamable HTTP MCP endpoints must use HTTPS.")
        if not parsed.hostname:
            raise ValueError("The MCP server URL must include a hostname.")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials must not be included in the MCP URL.")
        if parsed.query or parsed.fragment:
            raise ValueError(
                "MCP URLs must not contain query parameters or fragments."
            )

        hostname = parsed.hostname.rstrip(".").lower()
        if (
            hostname == "localhost"
            or hostname.endswith(".localhost")
            or hostname.endswith(".local")
            or hostname.endswith(".internal")
        ):
            raise ValueError("Local or internal MCP hostnames are not allowed.")

        try:
            port = parsed.port or 443
        except ValueError as exc:
            raise ValueError("The MCP server URL has an invalid port.") from exc
        if port not in self.allowed_http_ports:
            raise ValueError("The MCP server URL uses a blocked port.")

        try:
            literal_address = ipaddress.ip_address(hostname)
        except ValueError:
            try:
                resolved = set(self.host_resolver(hostname))
            except OSError as exc:
                raise ValueError(
                    "The MCP server hostname could not be resolved."
                ) from exc
            if not resolved:
                raise ValueError(
                    "The MCP server hostname did not resolve to an address."
                )
            addresses = resolved
        else:
            addresses = {str(literal_address)}

        if any(not _is_public_address(address) for address in addresses):
            raise ValueError(
                "The MCP server must resolve only to public network addresses."
            )

        return ValidatedMCPConnectionConfig(
            transport="streamable_http",
            server_url=normalized_url,
            stdio_template_code=None,
            configuration={},
        )
