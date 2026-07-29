from dataclasses import dataclass
from uuid import UUID
from typing import Any
# from sqlalchemy import UUID


from app.rag.embedder import GeminiEmbedder
from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)
from app.models.document_chunk import DocumentChunk
from app.rag.query_rewriter import QueryRewriter

@dataclass(slots=True)
class RetrievedChunk:
    document_id: UUID
    chunk_index: int
    chunk_text: str
    metadata: dict[str, Any]
    cosine_distance: float


class SemanticRetriever:

    def __init__(
        self,
        repository: DocumentChunkRepository,
        embedder: GeminiEmbedder,
    ):
        self.repository = repository
        self.embedder = embedder
        self.query_rewriter = QueryRewriter()

    def retrieve(
        self,
        question: str,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """
        Retrieve the top-k document chunks that are semantically
        similar to the user's question.

        Args:
            question: User's natural language question.
            top_k: Maximum number of chunks to retrieve.

        Returns:
            List of DocumentChunk objects ordered by similarity.
        """

        # Rewrite the user's question into a better semantic search query
        rewritten_query = self.query_rewriter.rewrite_query(question)

        # Generate embedding for the rewritten query
        try:
            query_embedding = self.embedder.generate_embedding(
                rewritten_query
            )
        except Exception as e:
            raise RuntimeError(
                "Failed to generate embedding for the rewritten query."
            ) from e

        # search for the most similar document chunks in the database
        try:
            results = self.repository.search_similar(
                query_embedding=query_embedding,
                top_k=top_k,
            )
        except Exception as e:
            raise RuntimeError(
                "Failed to retrieve similar document chunks from the database."
            ) from e

        retrieved_chunks = [
            RetrievedChunk(
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.chunk_text,
                metadata=chunk.chunk_metadata,
                cosine_distance=cosine_distance,
            )
            for chunk, cosine_distance in results
        ]

        return retrieved_chunks