"""
Citation Builder

This module converts retrieved document chunks into structured
source citations.

The CitationBuilder performs deterministic formatting only.

Responsibilities
----------------
- Extract citation metadata from retrieved chunks.
- Remove duplicate sources.
- Preserve retrieval order.
- Produce citation-ready output.

It does NOT:

- retrieve documents
- call Gemini
- generate answers
- rank sources
- summarize content
"""

from typing import Any

from app.rag.retriever import RetrievedChunk


class CitationBuilder:
    """
    Builds source citations from retrieved document chunks.

    The builder is deterministic. Given the same retrieved
    chunks it always returns the same citations.
    """

    def build_citations(
        self,
        retrieved_chunks: list[RetrievedChunk],
    ) -> list[dict[str, Any]]:
        """
        Build citations for retrieved chunks.

        Args:
            retrieved_chunks:
                Chunks returned by the retriever.

        Returns:
            Ordered list of unique citations.
        """

        if not retrieved_chunks:
            return []

        citations = []
        seen = set() 

        for chunk in retrieved_chunks:

            citation = self._build_single_citation(chunk)

            key = (
                citation["filename"],
                citation["page"],
            )

            if key in seen:
                continue

            seen.add(key)
            citations.append(citation)

        return citations

    def format_citations(
        self,
        citations: list[dict[str, Any]],
    ) -> str:
        """
        Convert citations into a human-readable string.

        Example

        Sources
        [1] Spring.pdf (Page 3)
        [2] Security.pdf
        """

        if not citations:
            return ""

        lines = ["Sources"]

        for index, citation in enumerate(
            citations,
            start=1,
        ):

            filename = citation["filename"]
            page = citation["page"]

            if page is None:
                lines.append(
                    f"[{index}] {filename}"
                )
            else:
                lines.append(
                    f"[{index}] {filename} (Page {page})"
                )

        return "\n".join(lines)

    def _build_single_citation(
        self,
        chunk: RetrievedChunk,
    ) -> dict[str, Any]:
        """
        Extract citation metadata from one chunk.
        """

        metadata = self._get_metadata(chunk)

        return {
            "document_id": metadata.get(
                "document_id"
            ),
            "filename": metadata.get(
                "filename",
                "Unknown Document",
            ),
            "page": metadata.get(
                "page"
            ),
            "chunk_index": chunk.chunk_index,
        }

    @staticmethod
    def _get_metadata(
        chunk: RetrievedChunk,
    ) -> dict[str, Any]:

        if chunk.metadata is None:
            return {}

        return chunk.metadata