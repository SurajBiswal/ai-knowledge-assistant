"""Public provider classes that feed native and MCP tools into one registry.

Availability rules decide what each authenticated user may see. The unified
factory checks collisions and produces the ToolRegistry consumed by LangGraph.
"""

from app.tools.providers.access import (
    StaticToolAvailabilityResolver,
    UserToolAvailability,
)
from app.tools.providers.base import ToolProvider
from app.tools.providers.mcp import MCPToolProvider
from app.tools.providers.native import NativeToolProvider
from app.tools.providers.unified import UnifiedToolRegistryFactory

__all__ = [
    "MCPToolProvider",
    "NativeToolProvider",
    "StaticToolAvailabilityResolver",
    "ToolProvider",
    "UnifiedToolRegistryFactory",
    "UserToolAvailability",
]
