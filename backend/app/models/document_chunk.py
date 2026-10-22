"""SQLAlchemy model for searchable pieces of uploaded documents.

RAG indexing splits extracted text into chunks and stores an embedding vector
for each chunk. Retrieval repositories compare query vectors with these values
and return the most relevant text to the document-search tool.
"""

import uuid
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, JSON, DateTime, func, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

from .document import Document
from typing import TYPE_CHECKING
from datetime import datetime

class DocumentChunk(Base):
    """Store one text chunk, its position, metadata, and embedding vector."""

    __tablename__ = "document_chunks"

    # Unique identifier for this searchable chunk.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Document that produced the chunk; deletion cascades from the document.
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # SQLAlchemy link to the parent Document record.
    document: Mapped["Document"] = relationship(
        back_populates="chunks"
    )

    # Actual passage returned to RAG context when this chunk matches a query.
    chunk_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Original position of this chunk within the source document.
    chunk_index: Mapped[int] = mapped_column(
        nullable=False,
    )

    # 768-number semantic representation used for vector similarity search.
    embedding: Mapped[list[float]] = mapped_column(
        Vector(768),
        nullable=False,
    )

    # Optional JSON details such as page or source information for citations.
    chunk_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    # Time this indexed chunk was stored.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )




    # PostgreSQL HNSW index speeds up cosine-similarity searches on embeddings.
    __table_args__ = (
        Index(
            "idx_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={
                "embedding": "vector_cosine_ops",
            },
            postgresql_with={
                "m": 16,
                "ef_construction": 64,
            },
        ),
    )
