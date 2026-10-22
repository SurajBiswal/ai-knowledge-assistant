"""add mcp connections and discovered tools

Revision ID: b6a2f0c4d911
Revises: 737105d3b7ea
Create Date: 2026-10-22 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b6a2f0c4d911"
down_revision: Union[str, Sequence[str], None] = "737105d3b7ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user-owned MCP connection and discovered-tool tables."""
    op.create_table(
        "mcp_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("transport", sa.String(length=30), nullable=False),
        sa.Column("server_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "stdio_template_code",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "auth_type",
            sa.String(length=30),
            server_default=sa.text("'none'"),
            nullable=False,
        ),
        sa.Column("encrypted_credentials", sa.Text(), nullable=True),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "timeout_seconds",
            sa.Integer(),
            server_default=sa.text("30"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'not_tested'"),
            nullable=False,
        ),
        sa.Column(
            "last_tested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_error_code",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "last_discovered_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "transport IN ('stdio', 'streamable_http')",
            name="ck_mcp_connections_transport",
        ),
        sa.CheckConstraint(
            "auth_type IN ('none', 'bearer', 'api_key_header')",
            name="ck_mcp_connections_auth_type",
        ),
        sa.CheckConstraint(
            "(auth_type = 'none' AND encrypted_credentials IS NULL) OR "
            "(auth_type IN ('bearer', 'api_key_header') "
            "AND encrypted_credentials IS NOT NULL)",
            name="ck_mcp_connections_credentials_match_auth",
        ),
        sa.CheckConstraint(
            "status IN ('not_tested', 'ready', 'error')",
            name="ck_mcp_connections_status",
        ),
        sa.CheckConstraint(
            "timeout_seconds > 0",
            name="ck_mcp_connections_timeout_positive",
        ),
        sa.CheckConstraint(
            "(transport = 'stdio' AND stdio_template_code IS NOT NULL "
            "AND server_url IS NULL) OR "
            "(transport = 'streamable_http' AND server_url IS NOT NULL "
            "AND stdio_template_code IS NULL)",
            name="ck_mcp_connections_transport_fields",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "name",
            name="uq_mcp_connections_user_name",
        ),
    )
    op.create_index(
        op.f("ix_mcp_connections_user_id"),
        "mcp_connections",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_mcp_connections_user_enabled",
        "mcp_connections",
        ["user_id", "is_enabled"],
        unique=False,
    )

    op.create_table(
        "mcp_connection_tools",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("remote_name", sa.String(length=255), nullable=False),
        sa.Column("public_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "input_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("schema_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "server_annotations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_available",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["mcp_connections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "connection_id",
            "remote_name",
            name="uq_mcp_connection_tools_remote_name",
        ),
        sa.UniqueConstraint(
            "connection_id",
            "public_name",
            name="uq_mcp_connection_tools_public_name",
        ),
    )
    op.create_index(
        op.f("ix_mcp_connection_tools_connection_id"),
        "mcp_connection_tools",
        ["connection_id"],
        unique=False,
    )
    op.create_index(
        "ix_mcp_connection_tools_connection_enabled",
        "mcp_connection_tools",
        ["connection_id", "is_enabled", "is_available"],
        unique=False,
    )


def downgrade() -> None:
    """Remove discovered tools first, then their parent connections."""
    op.drop_index(
        "ix_mcp_connection_tools_connection_enabled",
        table_name="mcp_connection_tools",
    )
    op.drop_index(
        op.f("ix_mcp_connection_tools_connection_id"),
        table_name="mcp_connection_tools",
    )
    op.drop_table("mcp_connection_tools")

    op.drop_index(
        "ix_mcp_connections_user_enabled",
        table_name="mcp_connections",
    )
    op.drop_index(
        op.f("ix_mcp_connections_user_id"),
        table_name="mcp_connections",
    )
    op.drop_table("mcp_connections")
