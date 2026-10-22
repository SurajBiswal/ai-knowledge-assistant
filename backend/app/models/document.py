"""SQLAlchemy model for files uploaded by users.

``DocumentService`` creates these records and the RAG service turns each file
into DocumentChunk records. Ownership is always checked with ``user_id``.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document_chunk import DocumentChunk


class Document(Base):
    """Store file metadata, processing state, owner, and searchable chunks."""

    __tablename__ = "documents"

    # Unique document ID used by APIs, chunks, and repositories.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # User who uploaded the file; deleting that user removes the document.
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Original filename shown to the user.
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Server-side path used when extracting or deleting the stored file.
    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    # File extension/type used by DocumentExtractor to choose a parser.
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Uploaded file size in bytes, returned in document API responses.
    file_size: Mapped[int] = mapped_column(
        nullable=False,
    )

    # Current upload/indexing state updated by DocumentService.
    status: Mapped[str] = mapped_column(
        String(50),
        default="uploaded",
        nullable=False,
    )

    # Time the database created the document record.
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # SQLAlchemy link back to the user who owns the document.
    user: Mapped["User"] = relationship(
        back_populates="documents"
    )

    # Searchable text pieces created by RAG indexing.
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
