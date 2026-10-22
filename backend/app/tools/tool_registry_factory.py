"""Build native-only or unified user-scoped tool registries.

The active Agent Node calls ``create_unified_tool_registry``. It combines
``NativeToolProvider`` with an optional ``MCPToolProvider`` and applies the
user's availability resolver. The sync helper remains for legacy code.
"""

from __future__ import annotations

from collections.abc import Callable
import inspect
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.mcp.client.manager import MCPClientManager
from app.tools.providers.access import (
    StaticToolAvailabilityResolver,
    ToolAvailabilityResolver,
)
from app.tools.providers.base import ToolProvider
from app.tools.providers.mcp import MCPToolProvider
from app.tools.providers.native import NativeToolProvider, build_native_tools
from app.tools.providers.unified import UnifiedToolRegistryFactory
from app.tools.registry import ToolRegistry


# This legacy helper still builds the original native-only registry for older
# scripts; the active LangGraph path uses create_unified_tool_registry below.
def create_tool_registry(
    db: Session,
    user_id: UUID,
) -> ToolRegistry:
    """Build the original synchronous registry containing only native tools."""

    registry = ToolRegistry()

    for tool in build_native_tools(db, user_id):
        registry.register(tool)

    return registry


# This async factory combines native tools with dynamically discovered MCP tools
# after applying the authenticated user's availability rules.
async def create_unified_tool_registry(
    db: Session,
    user_id: UUID,
    *,
    mcp_manager: MCPClientManager | None = None,
    availability_resolver: ToolAvailabilityResolver | None = None,
    providers: list[ToolProvider] | None = None,
) -> ToolRegistry:
    """Build one user's async unified registry from configured tool providers."""
    resolver = availability_resolver or StaticToolAvailabilityResolver()

    if providers is None:
        providers = [
            NativeToolProvider(
                db=db,
                availability_resolver=resolver,
            )
        ]

        if mcp_manager is not None:
            providers.append(
                MCPToolProvider(
                    manager=mcp_manager,
                    availability_resolver=resolver,
                )
            )

    factory = UnifiedToolRegistryFactory(providers)
    return await factory.create(user_id)


# This helper lets graph extensions provide either an async unified factory or
# an older synchronous factory while always giving graph nodes a real registry.
async def resolve_tool_registry(
    factory: Callable[..., Any],
    **kwargs: Any,
) -> ToolRegistry:
    """Run a sync or async registry factory and verify its result.

    Graph nodes use this compatibility helper so tests or older callers can
    still provide a synchronous factory while MCP-aware factories run
    asynchronously.
    """

    registry = factory(**kwargs)
    if inspect.isawaitable(registry):
        registry = await registry

    if not isinstance(registry, ToolRegistry) and not hasattr(
        registry,
        "get_all_tools",
    ):
        raise TypeError("Tool registry factory returned an invalid registry.")

    return registry
