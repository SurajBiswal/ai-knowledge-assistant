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
    """Expose the existing user-scoped RAG retrieval pipeline as a tool."""

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
        self.rag_service = rag_service
        self.user_id = user_id

    def execute(
        self,
        arguments: SearchDocumentsInput,
    ) -> SearchDocumentsOutput:
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
        metadata = chunk.metadata or {}

        document_name = (
            metadata.get("filename")
            or metadata.get("document_name")
            or str(chunk.document_id)
        )

        return DocumentSearchResult(
            document=str(document_name),
            chunk_index=int(chunk.chunk_index),
            content=chunk.chunk_text,
            score=float(chunk.score),
        )