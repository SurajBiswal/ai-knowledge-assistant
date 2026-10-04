"""add llm provider profiles

Revision ID: 737105d3b7ea
Revises: 42b59302bcf3
Create Date: 2026-09-12 09:51:41.807707
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "737105d3b7ea"
down_revision: Union[str, Sequence[str], None] = "42b59302bcf3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "llm_providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("protocol", sa.String(length=50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_llm_providers_code"),
        "llm_providers",
        ["code"],
        unique=True,
    )

    op.create_table(
        "llm_provider_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("profile_name", sa.String(length=100), nullable=False),
        sa.Column("base_url", sa.String(length=1000), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "structured_json_responses",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "last_tested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_test_status",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column(
            "last_test_error",
            sa.Text(),
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
            "timeout_seconds > 0",
            name="ck_llm_provider_profiles_timeout_positive",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["llm_providers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_llm_provider_profiles_provider_id"),
        "llm_provider_profiles",
        ["provider_id"],
        unique=False,
    )

    op.create_index(
        "ix_llm_provider_profiles_user_active",
        "llm_provider_profiles",
        ["user_id", "is_active"],
        unique=False,
    )

    op.create_index(
        op.f("ix_llm_provider_profiles_user_id"),
        "llm_provider_profiles",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "uq_llm_provider_profiles_one_active_per_user",
        "llm_provider_profiles",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active IS true"),
    )

    # Seed the initial system-supported provider.
    op.execute(
        sa.text(
            """
            INSERT INTO llm_providers (
                id,
                code,
                name,
                protocol,
                is_enabled
            )
            VALUES (
                '00000000-0000-0000-0000-000000000001',
                'openai_compatible',
                'OpenAI-compatible',
                'openai_compatible',
                true
            )
            """
        )
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "uq_llm_provider_profiles_one_active_per_user",
        table_name="llm_provider_profiles",
        postgresql_where=sa.text("is_active IS true"),
    )

    op.drop_index(
        op.f("ix_llm_provider_profiles_user_id"),
        table_name="llm_provider_profiles",
    )

    op.drop_index(
        "ix_llm_provider_profiles_user_active",
        table_name="llm_provider_profiles",
    )

    op.drop_index(
        op.f("ix_llm_provider_profiles_provider_id"),
        table_name="llm_provider_profiles",
    )

    op.drop_table("llm_provider_profiles")

    op.drop_index(
        op.f("ix_llm_providers_code"),
        table_name="llm_providers",
    )

    op.drop_table("llm_providers")