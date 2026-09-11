from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, document: Document) -> Document:
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def get_by_id(self, document_id: UUID) -> Document | None:
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
        stmt = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.uploaded_at.desc())
        )

        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def delete(self, document: Document) -> None:
        self.db.delete(document)
        self.db.commit()

    def update(self, document: Document) -> Document:
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
