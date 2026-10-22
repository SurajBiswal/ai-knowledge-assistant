"""Database operations for searchable DocumentChunk records.

RAG indexing stores chunks through this repository. SemanticRetriever performs
vector similarity searches here, while BM25Retriever loads all chunks belonging
to one user for keyword-based ranking.
"""

from uuid import UUID

from sqlalchemy import delete, select, and_
from sqlalchemy.orm import Session, joinedload

from app.models.document_chunk import DocumentChunk
from app.models.document import Document


class DocumentChunkRepository:
    """Store, list, delete, search, and count indexed document chunks."""

    def __init__(
        self,
        db: Session,
    ):
        """Store the SQLAlchemy session shared with the calling service."""
        self.db = db

    def create(
        self,
        chunk: DocumentChunk,
    ) -> DocumentChunk:
        """Save one indexed chunk and return its refreshed database record."""

        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)

        return chunk

    def list_by_document(
        self,
        document_id: UUID,
    ) -> list[DocumentChunk]:
        """Return a document's chunks in their original text order."""

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
        """Delete every chunk created from the selected document."""

        stmt = (
            delete(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )

        self.db.execute(stmt)
        self.db.commit()

    def search_similar(
            self,
            query_embedding: list[float],
            user_id: str | None = None,
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
        
        # pgvector calculates how far each stored vector is from the query.
        # A smaller cosine distance means the chunk is more similar.
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        stmt = (
            select(DocumentChunk,
                   distance.label("cosine_distance")
                )
            .join(Document)
        )

        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)

        stmt = stmt.order_by(distance).limit(top_k)
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
