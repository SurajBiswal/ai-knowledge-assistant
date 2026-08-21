"""
Cross Encoder Reranker

This module reranks retrieved document chunks using a
Cross-Encoder model.

Unlike vector search, which independently embeds the
query and document, a Cross Encoder evaluates the
(question, chunk) pair together and produces a
relevance score.

Responsibilities
----------------
- Load a Cross Encoder model.
- Score retrieved chunks.
- Sort chunks by relevance.
- Return the reranked chunks.

It does NOT:
- retrieve documents
- generate embeddings
- rewrite queries
- build prompts
"""

from sentence_transformers import CrossEncoder

from app.rag.retriever import RetrievedChunk


class CrossEncoderReranker:
    """
    Reranks retrieved chunks using a Cross Encoder.

    Pipeline

        Question
            +
        RetrievedChunk[]
                │
                ▼
        Cross Encoder
                │
                ▼
        RetrievedChunk[]
    """

    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
    ) -> None:
        """
        Initialize the reranker.

        Args:
            model_name:
                HuggingFace Cross Encoder model.
        """

        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        question: str,
        retrieved_chunks: list[RetrievedChunk],
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """
        Rerank retrieved chunks.

        Args:
            question:
                Original user question.

            retrieved_chunks:
                Candidate chunks from retrieval.

            top_k:
                Optional number of chunks to return.

        Returns:
            Chunks sorted by Cross Encoder relevance.
        """

        question = question.strip()

        if not question:
            raise ValueError(
                "Question cannot be empty."
            )

        if not retrieved_chunks:
            return []

        pairs = [
            (
                question,
                chunk.chunk_text,
            )
            for chunk in retrieved_chunks
        ]

        scores = self.model.predict(
            pairs,
            show_progress_bar=False,
        )

        scored_chunks = list(
            zip(
                scores,
                retrieved_chunks,
            )
        )

        scored_chunks.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        reranked_chunks = [
            chunk
            for _, chunk in scored_chunks
        ]

        if top_k is not None:
            reranked_chunks = reranked_chunks[:top_k]

        return reranked_chunks