from uuid import UUID

from sqlalchemy import delete, select, and_
from sqlalchemy.orm import Session, joinedload

from app.models.document_chunk import DocumentChunk
from app.models.document import Document


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
            user_id: str,
            top_k: int = 5,
    )-> list[tuple[DocumentChunk, float]]:
        
        """
        Retrieve the top-k document chunks whose embeddings are
        most similar to the provided query embedding.

        Similarity is calculated using pgvector cosine distance.

        Args:
            query_embedding: 768-dimensional query embedding.
            user_id: UUID of the user to filter documents by.
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
            .join(Document)
            .where(Document.user_id == user_id)
            .order_by(distance)
            .limit(top_k)
        )
        result = self.db.execute(stmt)
        return list(result.all())

    def list_all_chunks(self, user_id: str) -> list[DocumentChunk]:
        """
        Return all indexed document chunks for a specific user.

        Used by BM25Retriever to build the lexical index.

        Args:
            user_id: UUID of the user to filter documents by.
        """

        return (
            self.db.query(DocumentChunk)
            .join(Document)
            .filter(Document.user_id == user_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

    def count_by_user(self, user_id: UUID) -> int:
        """Return the number of chunks belonging to a user's documents."""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(DocumentChunk)
            .join(Document)
            .where(Document.user_id == user_id)
        )

        return int(self.db.execute(stmt).scalar_one())
