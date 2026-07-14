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

    def search_similar(
            self,
            query_embedding: list[float],
            top_k: int = 5,
    )-> list[tuple[DocumentChunk, float]]:
        
        """
        Retrieve the top-k document chunks whose embeddings are
        most similar to the provided query embedding.

        Similarity is calculated using pgvector cosine distance.

        Args:
            query_embedding: 768-dimensional query embedding.
            top_k: Maximum number of chunks to return.

        Returns:
            A list of DocumentChunk objects ordered from most
            similar to least similar.
        """
        
        distance = DocumentChunk.embedding.cosine_distance(query_embedding) # this is the pgvector function to calculate cosine distance between two vectors
        stmt = (
            select(DocumentChunk,
                   distance.label("cosine_distance")
                )
            .order_by(distance)
            .limit(top_k)
        )
        result = self.db.execute(stmt)
        return list(result.all())