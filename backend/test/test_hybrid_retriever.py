"""
Hybrid Retriever Validation

Validates the Week 8 - Part 5 hybrid retrieval pipeline against the
currently indexed document corpus.

Expected indexed documents:
    1. Technical Documentation for Odisha SSO Integration (Java – JSP & Servlet)
    2. The Secret of the Blue Observatory

Flow under test:

    User Question
          |
          v
    QueryRewriter
          |
          v
    HybridRetriever
       /          \
      v            v
 Semantic         BM25
 Retriever       Retriever
       \            /
        v          v
          Merge
            |
            v
        Deduplicate
            |
            v
          Top-K

Run from the backend directory:

    python3 test_hybrid_retriever.py
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.rag.bm25_retriever import BM25Retriever
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.retriever import RetrievedChunk, SemanticRetriever
from app.rag.embedder import GeminiEmbedder
from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)


TOP_K = 5

TEST_QUERIES = [
    # Semantic + lexical technical query.
    "How does JWT authentication work in the Odisha SSO integration?",

    # Strong BM25/keyword query.
    "What is the ID token validation process including issuer audience and signature?",

    # Query grounded in the second uploaded document.
    "Who visited the Blue Observatory in 2021 and what did he conclude?",
]


def _short_text(text: str, limit: int = 220) -> str:
    text = " ".join(text.split())
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def _source_name(chunk: RetrievedChunk) -> str:
    metadata = chunk.metadata or {}
    return (
        metadata.get("filename")
        or metadata.get("document_name")
        or str(chunk.document_id)
    )


def _print_results(
    title: str,
    results: Iterable[RetrievedChunk],
) -> list[RetrievedChunk]:
    results = list(results)

    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)

    if not results:
        print("No results.")
        return results

    for position, chunk in enumerate(results, start=1):
        print(f"\n[{position}]")
        print(f"Document : {_source_name(chunk)}")
        print(f"Chunk    : {chunk.chunk_index}")
        print(f"Score    : {chunk.score:.6f}")
        print(f"Text     : {_short_text(chunk.chunk_text)}")

    return results


def _assert_valid_results(
    results: list[RetrievedChunk],
    top_k: int,
) -> None:
    assert len(results) <= top_k, (
        f"Expected at most {top_k} results, got {len(results)}"
    )

    seen: set[tuple[object, int]] = set()

    for chunk in results:
        assert isinstance(chunk, RetrievedChunk)
        assert chunk.document_id is not None
        assert isinstance(chunk.chunk_index, int)
        assert chunk.chunk_text.strip()
        assert isinstance(chunk.metadata, dict)
        assert isinstance(chunk.score, float)

        key = (chunk.document_id, chunk.chunk_index)
        assert key not in seen, (
            "Duplicate chunk detected in hybrid results: "
            f"{key}"
        )
        seen.add(key)


def _assert_hybrid_is_subset_of_candidates(
    hybrid_results: list[RetrievedChunk],
    semantic_results: list[RetrievedChunk],
    bm25_results: list[RetrievedChunk],
) -> None:
    semantic_keys = {
        (chunk.document_id, chunk.chunk_index)
        for chunk in semantic_results
    }

    bm25_keys = {
        (chunk.document_id, chunk.chunk_index)
        for chunk in bm25_results
    }

    candidate_keys = semantic_keys | bm25_keys

    for chunk in hybrid_results:
        key = (chunk.document_id, chunk.chunk_index)

        assert key in candidate_keys, (
            "Hybrid returned a chunk that was not present in either "
            "semantic or BM25 candidate set: "
            f"{key}"
        )


def _print_overlap(
    semantic_results: list[RetrievedChunk],
    bm25_results: list[RetrievedChunk],
    hybrid_results: list[RetrievedChunk],
) -> None:
    semantic_keys = {
        (chunk.document_id, chunk.chunk_index)
        for chunk in semantic_results
    }

    bm25_keys = {
        (chunk.document_id, chunk.chunk_index)
        for chunk in bm25_results
    }

    hybrid_keys = {
        (chunk.document_id, chunk.chunk_index)
        for chunk in hybrid_results
    }

    overlap = semantic_keys & bm25_keys
    semantic_only = semantic_keys - bm25_keys
    bm25_only = bm25_keys - semantic_keys

    print("\n" + "-" * 90)
    print("HYBRID CONTRIBUTION")
    print("-" * 90)
    print(f"Semantic candidates : {len(semantic_keys)}")
    print(f"BM25 candidates     : {len(bm25_keys)}")
    print(f"Overlap             : {len(overlap)}")
    print(f"Semantic-only       : {len(semantic_only)}")
    print(f"BM25-only           : {len(bm25_only)}")
    print(f"Hybrid final        : {len(hybrid_keys)}")

    if bm25_only:
        print("\nBM25-only chunks contributed to the candidate pool:")
        for document_id, chunk_index in bm25_only:
            print(f"  - document={document_id}, chunk={chunk_index}")

    if not bm25_only:
        print(
            "\nNOTE: BM25 did not contribute a unique chunk for this query. "
            "This is not automatically a failure; it depends on the corpus "
            "and query."
        )


def _validate_basic_edge_cases(hybrid: HybridRetriever) -> None:
    print("\n" + "=" * 90)
    print("EDGE CASE VALIDATION")
    print("=" * 90)

    result = hybrid.retrieve(
        question="JWT authentication",
        top_k=0,
    )
    assert result == []
    print("[PASS] top_k=0 returns []")

    result = hybrid.retrieve(
        question="JWT authentication",
        top_k=-1,
    )
    assert result == []
    print("[PASS] negative top_k returns []")


def main() -> None:
    db: Session = SessionLocal()

    try:
        repository = DocumentChunkRepository(db=db)
        embedder = GeminiEmbedder()

        semantic_retriever = SemanticRetriever(
            repository=repository,
            embedder=embedder,
        )

        bm25_retriever = BM25Retriever(
            repository=repository,
        )

        hybrid_retriever = HybridRetriever(
            semantic_retriever=semantic_retriever,
            bm25_retriever=bm25_retriever,
        )

        print("=" * 90)
        print("WEEK 8 - PART 5: HYBRID RETRIEVER VALIDATION")
        print("=" * 90)
        print(f"Top-K: {TOP_K}")
        print()
        print("The test assumes the uploaded documents have already been")
        print("processed and their chunks are present in document_chunks.")

        # Force BM25 to build against the current database corpus.
        bm25_retriever.refresh_index()

        any_hybrid_results = False
        total_bm25_unique_contributions = 0

        for query_number, question in enumerate(TEST_QUERIES, start=1):
            print("\n\n" + "#" * 90)
            print(f"TEST QUERY {query_number}")
            print("#" * 90)
            print(f"\nQuestion:\n{question}")

            # Standalone retrieval results are useful for understanding
            # what each strategy contributes. HybridRetriever itself
            # performs its own query rewriting exactly once internally.
            semantic_results = semantic_retriever.retrieve(
                query=question,
                top_k=TOP_K,
            )

            bm25_results = bm25_retriever.retrieve(
                query=question,
                top_k=TOP_K,
            )

            hybrid_results = hybrid_retriever.retrieve(
                question=question,
                top_k=TOP_K,
            )

            _print_results(
                "SEMANTIC RETRIEVAL",
                semantic_results,
            )

            _print_results(
                "BM25 RETRIEVAL",
                bm25_results,
            )

            _print_results(
                "HYBRID RETRIEVAL",
                hybrid_results,
            )

            _assert_valid_results(
                hybrid_results,
                TOP_K,
            )

            _assert_hybrid_is_subset_of_candidates(
                hybrid_results=hybrid_results,
                semantic_results=semantic_results,
                bm25_results=bm25_results,
            )

            _print_overlap(
                semantic_results=semantic_results,
                bm25_results=bm25_results,
                hybrid_results=hybrid_results,
            )

            bm25_keys = {
                (chunk.document_id, chunk.chunk_index)
                for chunk in bm25_results
            }

            semantic_keys = {
                (chunk.document_id, chunk.chunk_index)
                for chunk in semantic_results
            }

            total_bm25_unique_contributions += len(
                bm25_keys - semantic_keys
            )

            if hybrid_results:
                any_hybrid_results = True

        _validate_basic_edge_cases(hybrid_retriever)

        assert any_hybrid_results, (
            "HybridRetriever returned no results for any test query. "
            "Check that the uploaded documents are indexed in the database."
        )

        print("\n" + "=" * 90)
        print("FINAL VALIDATION")
        print("=" * 90)

        if total_bm25_unique_contributions > 0:
            print(
                "[PASS] BM25 produced unique candidates for at least "
                "one test query."
            )
        else:
            print(
                "[INFO] No BM25-only candidates were observed in the "
                "selected queries. The hybrid implementation can still "
                "be valid, but BM25 contribution should be investigated "
                "with additional keyword-specific queries."
            )

        print("[PASS] Hybrid results contain valid RetrievedChunk objects.")
        print("[PASS] Hybrid results contain no duplicate document/chunk pairs.")
        print("[PASS] Hybrid results are drawn from semantic/BM25 candidates.")
        print("[PASS] top_k edge cases behave correctly.")

        print("\n" + "=" * 90)
        print("HYBRID RETRIEVER VALIDATION COMPLETED")
        print("=" * 90)

    finally:
        db.close()


if __name__ == "__main__":
    main()