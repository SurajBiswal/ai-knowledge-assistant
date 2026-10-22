"""Persist tools discovered from a user-owned MCP connection.

Discovery metadata is untrusted server-provided data. New tools are disabled,
annotations remain advisory, and repository queries join through the owning
connection so a tool ID alone never grants access.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.mcp_connection import MCPConnection


JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class MCPConnectionTool(Base):
    """Store one remote tool's latest schema and explicit trust state."""

    __tablename__ = "mcp_connection_tools"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Parent connection provides both server identity and user ownership.
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mcp_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Original name advertised by the MCP server.
    remote_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Stable name intended for the application's unified registry.
    public_name: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Original JSON input schema supplied by the server.
    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT,
        nullable=False,
    )

    # Hash makes schema changes visible and lets synchronization disable a tool
    # that changed after a user previously approved it.
    schema_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Server annotations are stored for display only. They never enable a tool
    # or replace application authorization checks.
    server_annotations: Mapped[dict[str, Any] | None] = mapped_column(
        JSON_DOCUMENT,
        nullable=True,
    )

    # Explicit trust must be granted by the owning user after discovery.
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # False means the tool disappeared during the latest discovery refresh.
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    connection: Mapped["MCPConnection"] = relationship(
        back_populates="tools"
    )

    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "remote_name",
            name="uq_mcp_connection_tools_remote_name",
        ),
        UniqueConstraint(
            "connection_id",
            "public_name",
            name="uq_mcp_connection_tools_public_name",
        ),
        Index(
            "ix_mcp_connection_tools_connection_enabled",
            "connection_id",
            "is_enabled",
            "is_available",
        ),
    )
