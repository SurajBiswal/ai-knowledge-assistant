"""Persist one user-owned MCP server connection definition.

This table stores safe metadata and encrypted credentials, not live SDK clients
or child-process state. Repositories always combine a connection ID with the
authenticated user's ID before returning or changing a record.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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
    from app.models.mcp_connection_tool import MCPConnectionTool
    from app.models.user import User


# JSON remains portable in unit tests while PostgreSQL uses efficient JSONB.
JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class MCPConnection(Base):
    """Store safe settings and encrypted authentication for one MCP server."""

    __tablename__ = "mcp_connections"

    # Stable identifier used by repositories and future management endpoints.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Owner taken from authenticated application context, never request data.
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Friendly user label; uniqueness is enforced within one user's account.
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Supported values are stdio and streamable_http.
    transport: Mapped[str] = mapped_column(String(30), nullable=False)

    # Public remote endpoint used only by Streamable HTTP connections.
    server_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    # Operator-approved template used only by stdio connections. No command or
    # user-provided executable is stored in this table.
    stdio_template_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Non-secret options allowed by the selected trusted template.
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT,
        default=dict,
        nullable=False,
    )

    # Authentication shape understood by a later runtime: none, bearer, or a
    # restricted API-key header. The actual values are encrypted separately.
    auth_type: Mapped[str] = mapped_column(
        String(30),
        default="none",
        nullable=False,
    )

    # One Fernet ciphertext containing credential JSON; never returned by safe
    # service representations and never placed in general configuration.
    encrypted_credentials: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Disabled by default until a later phase tests and explicitly enables it.
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Maximum seconds a later runtime may spend on a remote operation.
    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
    )

    # Persistent readiness information, not a claim that a live socket exists.
    status: Mapped[str] = mapped_column(
        String(30),
        default="not_tested",
        nullable=False,
    )
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    last_discovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    # Deleting a user removes connections; deleting a connection removes its
    # discovered tool rows through both ORM and database cascade rules.
    user: Mapped["User"] = relationship(back_populates="mcp_connections")
    tools: Mapped[list["MCPConnectionTool"]] = relationship(
        back_populates="connection",
        cascade="all, delete-orphan",
        order_by="MCPConnectionTool.remote_name",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "name",
            name="uq_mcp_connections_user_name",
        ),
        CheckConstraint(
            "transport IN ('stdio', 'streamable_http')",
            name="ck_mcp_connections_transport",
        ),
        CheckConstraint(
            "auth_type IN ('none', 'bearer', 'api_key_header')",
            name="ck_mcp_connections_auth_type",
        ),
        CheckConstraint(
            "(auth_type = 'none' AND encrypted_credentials IS NULL) OR "
            "(auth_type IN ('bearer', 'api_key_header') "
            "AND encrypted_credentials IS NOT NULL)",
            name="ck_mcp_connections_credentials_match_auth",
        ),
        CheckConstraint(
            "status IN ('not_tested', 'ready', 'error')",
            name="ck_mcp_connections_status",
        ),
        CheckConstraint(
            "timeout_seconds > 0",
            name="ck_mcp_connections_timeout_positive",
        ),
        CheckConstraint(
            "(transport = 'stdio' AND stdio_template_code IS NOT NULL "
            "AND server_url IS NULL) OR "
            "(transport = 'streamable_http' AND server_url IS NOT NULL "
            "AND stdio_template_code IS NULL)",
            name="ck_mcp_connections_transport_fields",
        ),
        Index(
            "ix_mcp_connections_user_enabled",
            "user_id",
            "is_enabled",
        ),
    )
