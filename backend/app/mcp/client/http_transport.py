"""Open Streamable HTTP MCP connections with stricter network defaults.

The MCP SDK normally creates its own HTTP client. This wrapper supplies a
client that never follows redirects, ignores proxy settings inherited from the
process environment, and keeps authentication headers only in runtime memory.

Hostname validation still cannot fully prevent DNS rebinding between the
application's DNS check and the network connection. Production deployments
should also restrict outbound traffic at the container, host, or network layer.
"""

from __future__ import annotations

from contextlib import AsyncExitStack
from types import TracebackType
from typing import Any, Mapping

import httpx2
from mcp.client._transport import TransportStreams
from mcp.client.streamable_http import streamable_http_client


class RestrictedStreamableHTTPTransport:
    """Give the MCP SDK an HTTP transport that rejects every redirect."""

    def __init__(
        self,
        *,
        url: str,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        """Store non-secret endpoint settings and runtime-only request headers."""
        self._url = url
        self._headers = dict(headers or {})
        self._timeout_seconds = timeout_seconds
        self._exit_stack: AsyncExitStack | None = None

    async def __aenter__(self) -> TransportStreams:
        """Open the HTTP client and MCP streams in the current owner task."""
        stack = AsyncExitStack()
        await stack.__aenter__()
        try:
            http_client = await stack.enter_async_context(
                httpx2.AsyncClient(
                    headers=self._headers,
                    timeout=self._timeout_seconds,
                    follow_redirects=False,
                    max_redirects=0,
                    trust_env=False,
                )
            )
            streams = await stack.enter_async_context(
                streamable_http_client(
                    self._url,
                    http_client=http_client,
                )
            )
        except BaseException:
            await stack.aclose()
            raise

        self._exit_stack = stack
        return streams

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Any:
        """Close MCP streams and the HTTP client in the same owner task."""
        stack = self._exit_stack
        self._exit_stack = None
        self._headers.clear()
        if stack is None:
            return None
        return await stack.__aexit__(exc_type, exc_value, traceback)
