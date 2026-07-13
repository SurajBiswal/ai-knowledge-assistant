from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk


class DocumentChunkRepository:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def create(
        self,
        chunk: DocumentChunk,
    ) -> DocumentChunk:

        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)

        return chunk

    def list_by_document(
        self,
        document_id: UUID,
    ) -> list[DocumentChunk]:

        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )

        result = self.db.execute(stmt)

        return list(result.scalars().all())

    def delete_by_document(
        self,
        document_id: UUID,
    ) -> None:

        stmt = (
            delete(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )

        self.db.execute(stmt)
        self.db.commit()