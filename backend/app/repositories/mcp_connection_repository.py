"""Database operations for user-owned MCP connection definitions.

Every read, update, and delete receives both ``connection_id`` and ``user_id``.
This keeps tenant isolation inside the database access layer rather than relying
on a caller to perform a separate ownership check.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mcp_connection import MCPConnection


class MCPConnectionRepository:
    """Persist MCP connections while requiring their authenticated owner."""

    def __init__(self, db: Session) -> None:
        """Store the request or test session used for database operations."""
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        name: str,
        transport: str,
        server_url: str | None,
        stdio_template_code: str | None,
        configuration: dict[str, Any],
        auth_type: str,
        encrypted_credentials: str | None,
        timeout_seconds: int,
    ) -> MCPConnection:
        """Add a disabled, untested connection to the current transaction."""
        connection = MCPConnection(
            user_id=user_id,
            name=name,
            transport=transport,
            server_url=server_url,
            stdio_template_code=stdio_template_code,
            configuration=configuration,
            auth_type=auth_type,
            encrypted_credentials=encrypted_credentials,
            is_enabled=False,
            timeout_seconds=timeout_seconds,
            status="not_tested",
        )
        self.db.add(connection)
        self.db.flush()
        return connection

    def get_by_id(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
    ) -> MCPConnection | None:
        """Return a connection only when its ID and owner both match."""
        statement = select(MCPConnection).where(
            MCPConnection.id == connection_id,
            MCPConnection.user_id == user_id,
        )
        return self.db.scalar(statement)

    def get_by_name(
        self,
        *,
        name: str,
        user_id: UUID,
    ) -> MCPConnection | None:
        """Find one connection name only inside the specified user's account."""
        statement = select(MCPConnection).where(
            MCPConnection.user_id == user_id,
            MCPConnection.name == name,
        )
        return self.db.scalar(statement)

    def list_by_user(self, *, user_id: UUID) -> list[MCPConnection]:
        """Return only connections owned by one authenticated user."""
        statement = (
            select(MCPConnection)
            .where(MCPConnection.user_id == user_id)
            .order_by(MCPConnection.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def record_test_result(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
        status: str,
        tested_at: datetime,
        error_code: str | None,
    ) -> MCPConnection | None:
        """Store a safe readiness result without persisting raw exceptions."""
        connection = self.get_by_id(
            connection_id=connection_id,
            user_id=user_id,
        )
        if connection is None:
            return None
        connection.status = status
        connection.last_tested_at = tested_at
        connection.last_error_code = error_code
        self.db.flush()
        return connection

    def update(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
        values: dict[str, Any],
    ) -> MCPConnection | None:
        """Apply validated editable fields to one connection owned by the user."""
        connection = self.get_by_id(
            connection_id=connection_id,
            user_id=user_id,
        )
        if connection is None:
            return None
        for field_name, value in values.items():
            setattr(connection, field_name, value)
        self.db.flush()
        return connection

    def set_enabled(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
        enabled: bool,
    ) -> MCPConnection | None:
        """Enable or disable an owned connection in the current transaction."""
        return self.update(
            connection_id=connection_id,
            user_id=user_id,
            values={"is_enabled": enabled},
        )

    def record_discovery(
        self,
        *,
        connection_id: UUID,
        user_id: UUID,
        discovered_at: datetime,
    ) -> MCPConnection | None:
        """Record when an owned connection last returned a tool list."""
        connection = self.get_by_id(
            connection_id=connection_id,
            user_id=user_id,
        )
        if connection is None:
            return None
        connection.last_discovered_at = discovered_at
        self.db.flush()
        return connection

    def delete(self, *, connection_id: UUID, user_id: UUID) -> bool:
        """Delete an owned connection and report whether it existed."""
        connection = self.get_by_id(
            connection_id=connection_id,
            user_id=user_id,
        )
        if connection is None:
            return False
        self.db.delete(connection)
        self.db.flush()
        return True
