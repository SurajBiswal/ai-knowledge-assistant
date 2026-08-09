from __future__ import annotations

import re
import threading
from heapq import nlargest

from rank_bm25 import BM25Okapi

from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)
from app.rag.retriever import RetrievedChunk

_TOKEN_PATTERN = re.compile(r"\b\w+\b")


class BM25Retriever:
    """
    Lexical retriever based on the BM25 ranking algorithm.

    Responsibilities:
    - Build and cache a BM25 index over document chunks
    - Rank chunks by lexical relevance
    - Return RetrievedChunk objects

    It does NOT:
    - Generate embeddings
    - Perform vector search
    - Call Gemini
    - Build prompts
    - Rewrite the query

    Note on query rewriting:
    This retriever expects an already-processed query string. Query
    rewriting is the caller's (e.g. HybridRetriever's) responsibility,
    so it happens exactly once per request instead of once per
    retriever. Keep in mind a rewrite tuned for semantic/embedding
    search (paraphrasing, expansion) can sometimes hurt BM25, which
    depends on literal term overlap — if retrieval quality matters a
    lot, consider whether BM25 should receive the raw question instead
    of the semantically-rewritten one.

    Notes on caching:
    The BM25 index is built once and cached in memory. Call
    `refresh_index()` whenever chunks are added, edited, or deleted
    so the index stays in sync with the underlying corpus.
    """

    def __init__(self, repository: DocumentChunkRepository):
        self.repository = repository

        self._bm25: BM25Okapi | None = None
        self._chunks: list = []
        self._lock = threading.Lock()

    def refresh_index(self) -> None:
        """
        Force a rebuild of the BM25 index on the next retrieve() call.
        Call this after documents are added, updated, or deleted.
        """
        with self._lock:
            self._bm25 = None
            self._chunks = []

    def _ensure_index(self) -> None:
        """
        Build the BM25 index lazily, once, and cache it.
        Thread-safe so concurrent requests don't race to rebuild it.
        """
        if self._bm25 is not None:
            return

        with self._lock:
            if self._bm25 is not None:
                # Another thread already built it while we waited.
                return

            chunks = self.repository.list_all_chunks()
            if not chunks:
                self._chunks = []
                self._bm25 = None
                return

            tokenized_corpus = [
                self._tokenize(chunk.chunk_text) for chunk in chunks
            ]
            self._chunks = chunks
            self._bm25 = BM25Okapi(tokenized_corpus)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[RetrievedChunk]:
        """
        Retrieve document chunks using BM25 lexical search.

        Args:
            query: The search query. Should already be rewritten by
                the caller if query rewriting is part of your pipeline.
            top_k: Maximum number of chunks to return.
            min_score: Chunks with a BM25 score at or below this value
                are dropped, since a score of 0 means no lexical
                overlap with the query at all.
        """
        if top_k <= 0:
            return []

        self._ensure_index()

        if self._bm25 is None:
            return []

        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []

        scores = self._bm25.get_scores(tokenized_query)

        # Only pull out the top_k best pairs instead of sorting the
        # entire corpus — matters once you have a large chunk count.
        top_pairs = nlargest(
            top_k,
            zip(self._chunks, scores),
            key=lambda pair: pair[1],
        )

        retrieved_chunks: list[RetrievedChunk] = []

        for chunk, score in top_pairs:
            if score <= min_score:
                break  # top_pairs is sorted descending, safe to stop

            retrieved_chunks.append(
                RetrievedChunk(
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.chunk_text,
                    metadata=chunk.chunk_metadata,
                    score=float(score),
                )
            )

        return retrieved_chunks

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """
        Tokenizer for BM25.

        Lowercases text and extracts word tokens, stripping punctuation
        so "chunks" and "chunks." are treated as the same token.
        """
        return _TOKEN_PATTERN.findall(text.lower())