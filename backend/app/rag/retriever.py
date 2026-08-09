from dataclasses import dataclass
from uuid import UUID
from typing import Any

from app.rag.embedder import GeminiEmbedder
from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)


@dataclass(slots=True)
class RetrievedChunk:
    document_id: UUID
    chunk_index: int
    chunk_text: str
    metadata: dict[str, Any]
    score: float


class SemanticRetriever:

    def __init__(
        self,
        repository: DocumentChunkRepository,
        embedder: GeminiEmbedder,
    ):
        self.repository = repository
        self.embedder = embedder

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        
        """
            Retrieve the top-k document chunks that are semantically
            similar to the supplied search query.

            This retriever assumes the query has already been
            preprocessed (for example, rewritten by the QueryRewriter).

            Responsibilities:
            - Generate a query embedding
            - Perform vector similarity search
            - Return RetrievedChunk objects

            It does NOT:
            - Rewrite queries
            - Build prompts
            - Merge retrieval results
        """


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