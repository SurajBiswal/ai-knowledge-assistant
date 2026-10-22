"""Per-user rules that control which native and MCP tools are visible.

Both providers ask a resolver for ``UserToolAvailability``. The current static
resolver supports configuration/tests; a later database resolver can implement
the same protocol without changing the graph or providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Protocol
from uuid import UUID


# This value object lists which native tools, MCP servers, and remote tools one
# user can access. None means "all" only after the server itself is allowed.
@dataclass(frozen=True, slots=True)
class UserToolAvailability:
    """Store the native tools and MCP servers one user may access.

    Provider classes call the ``allows_*`` methods before exposing tools to
    the agent. A value of ``None`` means no name-level restriction, while MCP
    servers still have to appear in ``mcp_server_names``.
    """

    # None allows every native tool; a set allows only names inside that set.
    native_tool_names: frozenset[str] | None = None
    # MCP access is denied unless a server name appears in this set.
    mcp_server_names: frozenset[str] = frozenset()
    # None allows every tool on allowed servers; a mapping narrows each server.
    mcp_tool_names: Mapping[str, frozenset[str]] | None = None

    # This check keeps native-tool filtering in one easy-to-read place.
    def allows_native_tool(self, tool_name: str) -> bool:
        """Return whether ``tool_name`` may be included for this user."""

        return (
            self.native_tool_names is None
            or tool_name in self.native_tool_names
        )

    # MCP access fails closed unless the server was explicitly allowed.
    def allows_mcp_server(self, server_name: str) -> bool:
        """Return whether the user may connect to this MCP server."""

        return server_name in self.mcp_server_names

    # This check optionally narrows an allowed MCP server to selected tools.
    def allows_mcp_tool(self, server_name: str, tool_name: str) -> bool:
        """Return whether one remote tool is allowed on an allowed server."""

        if not self.allows_mcp_server(server_name):
            return False

        if self.mcp_tool_names is None:
            return True

        return tool_name in self.mcp_tool_names.get(
            server_name,
            frozenset(),
        )


# A resolver hides where user permissions come from; a later phase can replace
# this with a database-backed resolver without changing either tool provider.
class ToolAvailabilityResolver(Protocol):
    """Interface for loading availability rules for an authenticated user."""

    async def resolve(self, user_id: UUID) -> UserToolAvailability:
        """Return the rule that should be applied to ``user_id``."""
        ...


# This resolver stores explicit per-user rules in memory and is also convenient
# for tests and application startup configuration.
@dataclass(slots=True)
class StaticToolAvailabilityResolver:
    """Read rules from an in-memory user mapping with a secure default."""

    # Explicit rules indexed by authenticated user UUID.
    availability_by_user: Mapping[UUID, UserToolAvailability] = field(
        default_factory=lambda: MappingProxyType({})
    )
    # Unknown users get all native tools and no MCP servers.
    default: UserToolAvailability = field(
        default_factory=UserToolAvailability
    )

    # The authenticated user ID selects the rule; unknown users receive the
    # secure default, which exposes native tools but no MCP server.
    async def resolve(self, user_id: UUID) -> UserToolAvailability:
        """Return ``user_id``'s stored rule or the secure default rule."""

        return self.availability_by_user.get(user_id, self.default)
