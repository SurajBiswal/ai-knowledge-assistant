from app.rag.bm25_retriever import BM25Retriever
from app.rag.retriever import (
    RetrievedChunk,
    SemanticRetriever,
)
from app.rag.query_rewriter import QueryRewriter
from uuid import UUID

class HybridRetriever:

    def __init__(
        self,
        semantic_retriever: SemanticRetriever,
        bm25_retriever: BM25Retriever,
    ):
        """
        Initialize the HybridRetriever.

        Args:
            semantic_retriever:
                Handles semantic (vector) retrieval.

            bm25_retriever:
                Handles keyword-based BM25 retrieval.
        """

        self.semantic_retriever = semantic_retriever
        self.bm25_retriever = bm25_retriever
        self.query_rewriter = QueryRewriter()

    def retrieve(
    self,
    question: str,
    top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """
    
            Retrieve relevant document chunks using a hybrid
            retrieval strategy.

            Workflow:
                1. Rewrite the user's question into a search query.
                2. Retrieve semantic (vector) results.
                3. Retrieve lexical (BM25) results.
                4. Merge and deduplicate the retrieved chunks.
                5. Return the final candidate chunks.

            ...
        """

        if top_k <= 0:
            return []

        query = self.query_rewriter.rewrite_query(
            question=question,
        )

        semantic_results = self._retrieve_semantic(
            query=query,
            top_k=top_k,
        )

        bm25_results = self._retrieve_bm25(
            query=query,
            top_k=top_k,
        )

        return self._merge_results(
            semantic_results=semantic_results,
            bm25_results=bm25_results,
            top_k=top_k,
        )

    


    def _retrieve_semantic(
    self,
    query: str,
    top_k: int,
    ) -> list[RetrievedChunk]:
        """
        Retrieve document chunks using semantic (vector) search.

        The query is expected to have already been rewritten by the
        HybridRetriever.

        Args:
            query:
                The search query.

            top_k:
                Maximum number of chunks to retrieve.

        Returns:
            Retrieved semantic chunks.
        """

        try:
            return self.semantic_retriever.retrieve(
                query=query,
                top_k=top_k,
            )

        except Exception as e:
            raise RuntimeError(
                "Semantic retrieval failed."
            ) from e

    

    def _retrieve_bm25(
    self,
    query: str,
    top_k: int,
    ) -> list[RetrievedChunk]:
        """
        Retrieve document chunks using BM25 lexical search.

        The query is expected to have already been rewritten by
        the HybridRetriever.

        Args:
            query:
                The search query.

            top_k:
                Maximum number of chunks to retrieve.

        Returns:
            Retrieved BM25 chunks ranked by lexical relevance.
        """

        try:
            return self.bm25_retriever.retrieve(
                query=query,
                top_k=top_k,
            )

        except Exception as e:
            raise RuntimeError(
                "BM25 retrieval failed."
            ) from e

        

    def _merge_results(
    self,
    semantic_results: list[RetrievedChunk],
    bm25_results: list[RetrievedChunk],
    top_k: int,
    ) -> list[RetrievedChunk]:
        """
        Merge semantic and BM25 retrieval results into a single
        candidate set.

        Workflow:
            1. Combine semantic and BM25 results.
            2. Remove duplicate chunks while preserving retrieval order.
            3. Limit the merged results to the requested top_k.
            4. Return the final candidate chunks.

        Note:
            Semantic results are placed before BM25 results so that
            semantic retrieval remains the primary retrieval strategy.
            BM25 contributes additional candidates that semantic search
            may have missed. Cross-encoder reranking will be introduced
            in a later stage of the pipeline.

        Args:
            semantic_results:
                Chunks returned by the SemanticRetriever.

            bm25_results:
                Chunks returned by the BM25Retriever.

            top_k:
                Maximum number of chunks to return.

        Returns:
            A merged and deduplicated list of RetrievedChunk objects.
        """

        candidate_chunks = (
            semantic_results
            + bm25_results
        )

        merged_chunks = self._deduplicate(
            candidate_chunks,
        )

        return merged_chunks[:top_k]


    def _deduplicate(
    self,
    chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """
        Remove duplicate retrieved chunks while preserving their
        original retrieval order.

        Chunks are considered duplicates if they originate from the
        same document and have the same chunk index. The first
        occurrence is retained and later duplicates are discarded.

        Args:
            chunks:
                The merged list of retrieved chunks.

        Returns:
            A deduplicated list of RetrievedChunk objects.
        """

        seen: set[tuple[UUID, int]] = set()
        unique_chunks: list[RetrievedChunk] = []

        for chunk in chunks:
            chunk_key = (
                chunk.document_id,
                chunk.chunk_index,
            )

            if chunk_key in seen:
                continue

            seen.add(chunk_key)
            unique_chunks.append(chunk)

        return unique_chunks