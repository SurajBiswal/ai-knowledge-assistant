"""
Context Builder

This module converts retrieved document chunks into a structured text
context that can be passed to the LLM as part of a grounded prompt.

The ContextBuilder performs deterministic formatting only.

Responsibilities:
- Format retrieved document chunks.
- Preserve retrieval ordering.
- Produce a prompt-ready context string.

It does NOT:
- retrieve documents
- generate embeddings
- call Gemini
- summarize content
- generate answers
"""

from typing import Any

from app.rag.retriever import RetrievedChunk


class ContextBuilder:
    """
    Builds a structured text context from retrieved document chunks.

    The returned context is intended to be injected into the prompt
    before calling the language model.
    """

    SEPARATOR = "\n" + ("-" * 80) + "\n"

    def build_context(
        self,
        retrieved_chunks: list[RetrievedChunk],
    ) -> str:
        """
        Build a structured context string from retrieved chunks.

        Args:
            retrieved_chunks:
                List of RetrievedChunk objects ordered by retrieval
                relevance.

        Returns:
            A formatted context string ready for prompt construction.

            Returns an empty string when no chunks are available.
        """

        if not retrieved_chunks:
            return ""

        # context_sections = [
        #     self._format_chunk(chunk)
        #     for chunk in retrieved_chunks
        # ]

        context_sections = []

        for chunk in retrieved_chunks:
            formatted = self._format_chunk(chunk)
            context_sections.append(formatted)

        return self.SEPARATOR.join(context_sections)

    def _format_chunk(
        self,
        chunk: RetrievedChunk,
    ) -> str:
        """
        Format a single retrieved chunk.

        Args:
            chunk:
                RetrievedChunk instance.

        Returns:
            A formatted chunk section.
        """

        metadata = self._get_metadata(chunk)

        filename = metadata.get(
            "filename",
            "Unknown Document",
        )

        # page = metadata.get(
        #     "page",
        #     "Unknown",
        # )

        page = metadata.get("page") or "Unknown"

        chunk_text = chunk.chunk_text.strip()

        return (
            f"Source: {filename}\n"
            f"Chunk: {chunk.chunk_index}\n"
            f"Page: {page}\n\n"
            f"{chunk_text}"
        )

    @staticmethod
    def _get_metadata(
        chunk: RetrievedChunk,
    ) -> dict[str, Any]:
        """
        Safely retrieve metadata from a chunk.

        Args:
            chunk:
                RetrievedChunk instance.

        Returns:
            Metadata dictionary.
        """

        if chunk.metadata is None:
            return {}

        return chunk.metadata