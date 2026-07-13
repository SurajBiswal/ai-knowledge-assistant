import uuid
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, JSON, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

from .document import Document
from typing import TYPE_CHECKING
from datetime import datetime

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    document: Mapped["Document"] = relationship(
        back_populates="chunks"
    )

    chunk_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(
        nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(768),
        nullable=False,
    )

    chunk_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

