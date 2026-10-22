"""Combine tools from many providers into one safe ToolRegistry.

The factory asks providers for user-filtered tools in order, registers them,
and rejects duplicate public names before the LLM sees an ambiguous definition.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.tools.providers.base import ToolProvider
from app.tools.registry import ToolNameCollisionError, ToolRegistry


# This factory asks every provider for the current user's tools and combines
# them into the one registry already used by the agent and Tool Node.
class UnifiedToolRegistryFactory:
    """Collect user-filtered tools from providers into one registry."""

    # Providers stay in order so native tools and discovered tools are exposed
    # to the LLM in a predictable order.
    def __init__(self, providers: Sequence[ToolProvider]) -> None:
        """Store providers in the order their tools should reach the LLM."""
        self.providers = list(providers)

    # Registration happens in one place so name collisions are detected before
    # the LLM can request an ambiguous tool.
    async def create(self, user_id: UUID) -> ToolRegistry:
        """Collect allowed tools for ``user_id`` and return one checked registry."""
        registry = ToolRegistry()
        tool_sources: dict[str, str] = {}

        for provider in self.providers:
            tools = await provider.get_tools(user_id)

            for tool in tools:
                tool_name = getattr(tool, "name", None)
                current_source = _describe_tool_source(provider, tool)
                if tool_name in tool_sources:
                    previous_source = tool_sources[tool_name]
                    raise ToolNameCollisionError(
                        f"Tool name collision for '{tool_name}' between "
                        f"'{previous_source}' and '{current_source}'."
                    )

                registry.register(tool)
                tool_sources[tool_name] = current_source

        return registry


# This helper includes an MCP server name in collision errors, making it clear
# which two remote servers produced the same normalized public tool name.
def _describe_tool_source(provider: ToolProvider, tool: object) -> str:
    server_name = getattr(tool, "server_name", None)
    if server_name:
        return f"{provider.name} server {server_name}"

    return provider.name
