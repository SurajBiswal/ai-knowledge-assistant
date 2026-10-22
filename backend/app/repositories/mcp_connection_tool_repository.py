"""Database operations for tools discovered from MCP connections.

Tool ownership is inherited from the parent connection. Every public lookup
joins ``mcp_connections`` and checks ``user_id`` so knowing a tool UUID is never
enough to read, enable, or change another user's tool.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mcp_connection import MCPConnection
from app.models.mcp_connection_tool import MCPConnectionTool


class MCPConnectionToolRepository:
    """Persist discovered tools with connection ownership in every operation."""

    def __init__(self, db: Session) -> None:
        """Store the SQLAlchemy session shared with the connection service."""
        self.db = db

    def _owned_connection_exists(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Return whether the connection belongs to the authenticated user."""
        statement = select(MCPConnection.id).where(
            MCPConnection.id == connection_id,
            MCPConnection.user_id == user_id,
        )
        return self.db.scalar(statement) is not None

    def list_by_connection(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
    ) -> list[MCPConnectionTool]:
        """List tools only after joining through an owned connection."""
        statement = (
            select(MCPConnectionTool)
            .join(
                MCPConnection,
                MCPConnection.id == MCPConnectionTool.connection_id,
            )
            .where(
                MCPConnectionTool.connection_id == connection_id,
                MCPConnection.user_id == user_id,
            )
            .order_by(MCPConnectionTool.remote_name)
        )
        return list(self.db.scalars(statement).all())

    def get_by_id(
        self,
        *,
        tool_id: UUID,
        connection_id: UUID,
        user_id: UUID,
    ) -> MCPConnectionTool | None:
        """Return a tool only when tool, connection, and owner all match."""
        statement = (
            select(MCPConnectionTool)
            .join(
                MCPConnection,
                MCPConnection.id == MCPConnectionTool.connection_id,
            )
            .where(
                MCPConnectionTool.id == tool_id,
                MCPConnectionTool.connection_id == connection_id,
                MCPConnection.user_id == user_id,
            )
        )
        return self.db.scalar(statement)

    def synchronize_discovered(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
        discovered_tools: Iterable[dict[str, Any]],
        discovered_at: datetime,
    ) -> list[MCPConnectionTool]:
        """Refresh metadata while disabling new, removed, or changed tools."""
        if not self._owned_connection_exists(
            connection_id=connection_id,
            user_id=user_id,
        ):
            raise ValueError("MCP connection not found.")

        existing_tools = {
            tool.remote_name: tool
            for tool in self.list_by_connection(
                connection_id=connection_id,
                user_id=user_id,
            )
        }

        # Mark every existing tool unseen first. Tools that remain missing after
        # this refresh become unavailable and lose any previous approval.
        for tool in existing_tools.values():
            tool.is_available = False

        synchronized: list[MCPConnectionTool] = []
        for discovered in discovered_tools:
            remote_name = discovered["remote_name"]
            tool = existing_tools.get(remote_name)

            if tool is None:
                tool = MCPConnectionTool(
                    connection_id=connection_id,
                    remote_name=remote_name,
                    public_name=discovered["public_name"],
                    description=discovered["description"],
                    input_schema=discovered["input_schema"],
                    schema_hash=discovered["schema_hash"],
                    server_annotations=discovered["server_annotations"],
                    is_enabled=False,
                    is_available=True,
                    last_seen_at=discovered_at,
                )
                self.db.add(tool)
            else:
                schema_changed = tool.schema_hash != discovered["schema_hash"]
                tool.public_name = discovered["public_name"]
                tool.description = discovered["description"]
                tool.input_schema = discovered["input_schema"]
                tool.schema_hash = discovered["schema_hash"]
                tool.server_annotations = discovered["server_annotations"]
                tool.is_available = True
                tool.last_seen_at = discovered_at
                if schema_changed:
                    tool.is_enabled = False

            synchronized.append(tool)

        for tool in existing_tools.values():
            if not tool.is_available:
                tool.is_enabled = False

        self.db.flush()
        return synchronized

    def set_enabled(
        self,
        *,
        tool_id: UUID,
        connection_id: UUID,
        user_id: UUID,
        enabled: bool,
    ) -> MCPConnectionTool | None:
        """Change explicit trust only for an available tool owned by the user."""
        tool = self.get_by_id(
            tool_id=tool_id,
            connection_id=connection_id,
            user_id=user_id,
        )
        if tool is None:
            return None
        if enabled and not tool.is_available:
            raise ValueError("An unavailable MCP tool cannot be enabled.")
        tool.is_enabled = enabled
        self.db.flush()
        return tool

    def disable_all(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
        mark_unavailable: bool,
    ) -> list[MCPConnectionTool]:
        """Revoke every approval after the connection target or secret changes."""
        tools = self.list_by_connection(
            connection_id=connection_id,
            user_id=user_id,
        )
        for tool in tools:
            tool.is_enabled = False
            if mark_unavailable:
                tool.is_available = False
        self.db.flush()
        return tools
