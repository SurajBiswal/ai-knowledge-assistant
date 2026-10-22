"""Shared retrieval result and semantic vector-search implementation.

``SemanticRetriever`` embeds a search query and asks
``DocumentChunkRepository`` for nearby vectors. It returns ``RetrievedChunk``
objects used by hybrid retrieval, reranking, context, and citation builders.
"""

from dataclasses import dataclass
from uuid import UUID
from typing import Any

from app.rag.embedder import GeminiEmbedder
from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)


@dataclass(slots=True)
class RetrievedChunk:
    """Provider-independent representation of one retrieved document passage."""

    # Source document and original chunk position identify the passage.
    document_id: UUID
    chunk_index: int
    # Text and source details are used to build LLM context and citations.
    chunk_text: str
    metadata: dict[str, Any]
    # Retrieval score names are kept in sync for compatibility with callers.
    score: float | None = None
    cosine_distance: float | None = None

    def __post_init__(self) -> None:
        """Copy the available score name into the compatibility field."""
        if self.score is None and self.cosine_distance is not None:
            self.score = self.cosine_distance
        if self.cosine_distance is None and self.score is not None:
            self.cosine_distance = self.score


class SemanticRetriever:
    """Find user-owned chunks whose embeddings are close to the query vector."""

    def __init__(
        self,
        repository: DocumentChunkRepository,
        embedder: GeminiEmbedder,
    ):
        """Store the chunk repository and embedding client used by retrieval."""
        self.repository = repository
        self.embedder = embedder

    def retrieve(
        self,
        query: str | None = None,
        question: str | None = None,
        user_id: str | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Embed ``query``/``question`` and return the closest stored chunks."""

        if query is None:
            query = question

        if query is None:
            raise ValueError("Query or question is required.")
        
        try:
            query_embedding = (
                self.embedder.generate_embedding(
                    query
                )
            )

        except Exception as e:
            raise RuntimeError(
                "Failed to generate embedding."
            ) from e

        try:
            results = self.repository.search_similar(
                query_embedding=query_embedding,
                user_id=user_id,
                top_k=top_k,
            )

        except Exception as e:
            raise RuntimeError(
                "Failed to retrieve similar chunks."
            ) from e

        retrieved_chunks = [
            RetrievedChunk(
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.chunk_text,
                metadata=chunk.chunk_metadata,
                score=cosine_distance,
            )
            for chunk, cosine_distance in results
        ]

        return retrieved_chunks
