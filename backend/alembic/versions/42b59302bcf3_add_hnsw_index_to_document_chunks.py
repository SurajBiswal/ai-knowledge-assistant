"""add hnsw index to document_chunks

Revision ID: 42b59302bcf3
Revises: 1bdfce714bb4
Create Date: 2026-07-08 12:10:21.117246
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "42b59302bcf3"
down_revision: Union[str, Sequence[str], None] = "1bdfce714bb4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE INDEX idx_chunks_embedding
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (
            m = 16,
            ef_construction = 64
        )
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        DROP INDEX IF EXISTS idx_chunks_embedding
    """)