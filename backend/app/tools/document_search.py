"""Native tool that searches the authenticated user's uploaded documents.

The LLM selects this tool when a question needs personal document knowledge.
It calls ``RAGService.retrieve`` and converts retrieved chunks into the validated
output shape returned to the model.
"""

from __future__ import annotations

from app.rag.retriever import RetrievedChunk
from app.services.rag_service import RAGService
from app.tools.base import BaseTool
from app.tools.schemas import (
    DocumentSearchResult,
    SearchDocumentsInput,
    SearchDocumentsOutput,
)


class DocumentSearchTool(
    BaseTool[SearchDocumentsInput, SearchDocumentsOutput]
):
    """Expose user-scoped document retrieval as ``search_documents``."""

    name = "search_documents"

    description = (
        "Search the authenticated user's uploaded knowledge base for "
        "information relevant to a query. Use this tool when the answer "
        "may be contained in the user's uploaded documents. Returns the "
        "most relevant document chunks with their source document, chunk "
        "index, content, and relevance score."
    )

    input_schema = SearchDocumentsInput
    output_schema = SearchDocumentsOutput

    def __init__(self, rag_service: RAGService, user_id: str) -> None:
        """Store the RAG pipeline and trusted authenticated user ID."""
        self.rag_service = rag_service
        self.user_id = user_id

    def execute(
        self,
        arguments: SearchDocumentsInput,
    ) -> SearchDocumentsOutput:
        """Validate arguments, retrieve owned chunks, and return safe results."""
        validated_arguments = self.validate_input(arguments)

        retrieved_chunks = self.rag_service.retrieve(
            question=validated_arguments.query,
            user_id=self.user_id,
            top_k=validated_arguments.top_k,
        )

        results = [
            self._to_result(chunk)
            for chunk in retrieved_chunks
        ]

        return self.validate_output(
            SearchDocumentsOutput(results=results)
        )

    @staticmethod
    def _to_result(chunk: RetrievedChunk) -> DocumentSearchResult:
        """Convert one internal retrieved chunk into public tool output."""
        metadata = chunk.metadata or {}

        document_name = (
            metadata.get("filename")
            or metadata.get("document_name")
            or str(chunk.document_id)
        )

        document_id = metadata.get("document_id") or str(chunk.document_id)
        page = metadata.get("page")
        if isinstance(page, bool) or not isinstance(page, int):
            page = None

        return DocumentSearchResult(
            document_id=str(document_id),
            document=str(document_name),
            page=page,
            chunk_index=int(chunk.chunk_index),
            content=chunk.chunk_text,
            score=float(chunk.score),
        )
