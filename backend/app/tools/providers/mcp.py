"""Discover and adapt remote MCP tools for one authenticated user.

The provider reads safe server status from ``MCPClientManager``, skips servers
the user cannot access, refreshes discovery, filters remote tool names, and
returns ``MCPToolAdapter`` instances for unified registration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.mcp.adapters.tool_adapter import MCPToolAdapter
from app.tools.providers.access import ToolAvailabilityResolver
from app.tools.providers.base import ToolProvider

if TYPE_CHECKING:
    from app.mcp.client.manager import MCPClientManager


# This provider connects to every MCP server allowed for the user, discovers
# its current tools, and adapts those tools to the application's tool contract.
class MCPToolProvider(ToolProvider):
    """Turn allowed tools from several MCP servers into local adapters."""

    name = "mcp"

    # The manager owns connections; the provider only discovers and adapts tools
    # so connection lifetime can be managed centrally by the application.
    def __init__(
        self,
        manager: MCPClientManager,
        availability_resolver: ToolAvailabilityResolver,
    ) -> None:
        self.manager = manager  # Owns all configured MCP connections.
        self.availability_resolver = availability_resolver  # User access rules.

    # Each call refreshes discovery for all allowed servers, so newly added or
    # removed MCP tools are reflected in the next conversation turn.
    async def get_tools(self, user_id: UUID) -> list[Any]:
        """Discover and adapt every remote tool available to ``user_id``."""

        availability = await self.availability_resolver.resolve(user_id)
        adapters: list[Any] = []

        for server in self.manager.list_servers():
            server_name = server["name"]

            if not availability.allows_mcp_server(server_name):
                continue

            if server["status"] != "connected":
                await self.manager.connect(server_name)

            discovered_tools = await self.manager.discover_tools(server_name)

            for discovered in discovered_tools:
                remote_name = discovered["name"]
                if not availability.allows_mcp_tool(
                    server_name,
                    remote_name,
                ):
                    continue

                adapters.append(
                    MCPToolAdapter(
                        manager=self.manager,
                        server_name=server_name,
                        remote_tool_name=remote_name,
                        description=discovered.get("description"),
                        input_schema=discovered["input_schema"],
                    )
                )

        return adapters
