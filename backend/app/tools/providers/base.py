"""Common interface implemented by every source of application tools.

The unified registry factory can combine any provider that returns tools for an
authenticated user. Async is used because MCP discovery may require network or
subprocess communication.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


# A tool provider knows where a group of tools comes from and returns only the
# tools that the current authenticated user is allowed to use.
class ToolProvider(ABC):
    """Define how a source returns tools allowed for one user.

    ``UnifiedToolRegistryFactory`` uses this interface for both built-in tools
    and remotely discovered MCP tools.
    """

    # This short label identifies the provider in name-collision error messages.
    name: str

    # Providers use one async interface because MCP discovery needs network I/O,
    # even though native providers can build their tools immediately.
    @abstractmethod
    async def get_tools(self, user_id: UUID) -> list[Any]:
        """Return only tools this provider makes available to ``user_id``."""
        raise NotImplementedError
