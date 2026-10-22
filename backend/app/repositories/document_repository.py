"""Database operations for uploaded Document records.

DocumentService and RAGService use this repository to store file metadata,
enforce user ownership in lookups, update processing status, and count files.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


class DocumentRepository:
    """Provide document queries using one SQLAlchemy session."""

    def __init__(self, db: Session):
        """Store the request's database session for later document operations."""
        self.db = db

    def create(self, document: Document) -> Document:
        """Save a new Document model and return it with database values loaded."""
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def get_by_id(self, document_id: UUID) -> Document | None:
        """Find a document by ID without applying an ownership filter."""
        stmt = (
            select(Document)
            .where(Document.id == document_id)
        )

        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_id_and_user(
        self,
        document_id: UUID,
        user_id: UUID,
    ) -> Document | None:
        """Find a document only when both its ID and owner match."""
        stmt = (
            select(Document)
            .where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )

        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def list_by_user(
        self,
        user_id: UUID,
    ) -> list[Document]:
        """Return one user's documents with the newest upload first."""
        stmt = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.uploaded_at.desc())
        )

        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def delete(self, document: Document) -> None:
        """Delete the supplied document record and commit the change."""
        self.db.delete(document)
        self.db.commit()

    def update(self, document: Document) -> Document:
        """Save changes to an existing document and return the refreshed record."""
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def count_by_user(self, user_id: UUID) -> int:
        """Return the number of documents owned by a user."""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(Document)
            .where(Document.user_id == user_id)
        )

        return int(self.db.execute(stmt).scalar_one())
