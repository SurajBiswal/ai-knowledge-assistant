"""Focused tests for the Phase 2 MCP transport security boundary."""

from __future__ import annotations

import sys

import pytest

from app.mcp.config.stdio_templates import ApprovedStdioServerTemplate
from app.mcp.security.connection_validation import (
    MCPConnectionConfigValidator,
)


def make_validator(*, resolved_addresses=("8.8.8.8",)):
    """Build a validator with one test template and deterministic DNS results."""
    template = ApprovedStdioServerTemplate(
        code="safe_echo",
        name="Safe Echo",
        command=sys.executable,
        fixed_args=("/trusted/echo_server.py",),
        allowed_configuration_keys=frozenset({"workspace"}),
    )
    return MCPConnectionConfigValidator(
        stdio_templates={template.code: template},
        host_resolver=lambda _hostname: resolved_addresses,
    )


def test_stdio_requires_an_approved_template_and_known_options() -> None:
    """Prove a user cannot persist an arbitrary command-shaped configuration."""
    validator = make_validator()

    validated = validator.validate(
        transport="stdio",
        stdio_template_code="safe_echo",
        configuration={"workspace": "user-a"},
    )

    assert validated.stdio_template_code == "safe_echo"
    assert validated.server_url is None
    assert validated.configuration == {"workspace": "user-a"}

    with pytest.raises(ValueError, match="approved stdio"):
        validator.validate(
            transport="stdio",
            stdio_template_code="user-supplied-command",
        )

    with pytest.raises(ValueError, match="Unsupported stdio"):
        validator.validate(
            transport="stdio",
            stdio_template_code="safe_echo",
            configuration={"command": "/bin/sh"},
        )


def test_stdio_general_configuration_rejects_secret_fields() -> None:
    """Prove secret-like data cannot be placed in the safe JSON document."""
    template = ApprovedStdioServerTemplate(
        code="bad_option_test",
        name="Bad Option Test",
        command=sys.executable,
        allowed_configuration_keys=frozenset({"api_token"}),
    )
    validator = MCPConnectionConfigValidator(
        stdio_templates={template.code: template},
    )

    with pytest.raises(ValueError, match="Secrets are not allowed"):
        validator.validate(
            transport="stdio",
            stdio_template_code=template.code,
            configuration={"api_token": "must-not-be-stored-here"},
        )


@pytest.mark.parametrize(
    "url, expected_message",
    [
        ("http://mcp.example.com/mcp", "must use HTTPS"),
        ("https://user:pass@mcp.example.com/mcp", "must not be included"),
        ("https://localhost/mcp", "Local or internal"),
        ("https://127.0.0.1/mcp", "public network"),
        ("https://169.254.169.254/latest", "public network"),
        ("https://mcp.example.com:8443/mcp", "blocked port"),
        ("https://mcp.example.com/mcp?token=secret", "query parameters"),
    ],
)
def test_http_rejects_unsafe_endpoint_shapes(
    url: str,
    expected_message: str,
) -> None:
    """Reject common URL-based credential leaks and SSRF destinations."""
    validator = make_validator()

    with pytest.raises(ValueError, match=expected_message):
        validator.validate(
            transport="streamable_http",
            server_url=url,
        )


def test_http_rejects_hostname_resolving_to_private_address() -> None:
    """Validate DNS results rather than trusting a public-looking hostname."""
    validator = make_validator(resolved_addresses=("10.20.30.40",))

    with pytest.raises(ValueError, match="public network"):
        validator.validate(
            transport="streamable_http",
            server_url="https://mcp.example.com/mcp",
        )


def test_http_accepts_a_public_https_endpoint() -> None:
    """Keep a valid Streamable HTTP endpoint and explicit empty configuration."""
    validator = make_validator()

    validated = validator.validate(
        transport="streamable_http",
        server_url="https://mcp.example.com/mcp",
    )

    assert validated.transport == "streamable_http"
    assert validated.server_url == "https://mcp.example.com/mcp"
    assert validated.stdio_template_code is None
    assert validated.configuration == {}
