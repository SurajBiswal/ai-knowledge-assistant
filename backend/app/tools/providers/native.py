"""Create the application's built-in tools for one authenticated user.

This module preserves the existing RAG, workspace-statistics, and web-search
construction. ``NativeToolProvider`` filters those tools with the same per-user
availability rules used by MCP tools.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.rag.bm25_retriever import BM25Retriever
from app.rag.cross_encoder_reranker import CrossEncoderReranker
from app.rag.embedder import GeminiEmbedder
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.retriever import SemanticRetriever
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.message_repository import MessageRepository
from app.services.rag_service import RAGService
from app.services.web_search_service import WebSearchService
from app.tools.document_search import DocumentSearchTool
from app.tools.providers.access import ToolAvailabilityResolver
from app.tools.providers.base import ToolProvider
from app.tools.web_search import WebSearchTool
from app.tools.workspace_stats import WorkspaceStatsTool


# This function builds the application's original tools with the authenticated
# user ID, preserving the existing RAG, statistics, and web-search behavior.
def build_native_tools(db: Session, user_id: UUID) -> list[Any]:
    """Build the three built-in tools for one authenticated user.

    The database session is passed into repositories, and ``user_id`` is
    stored inside user-scoped tools so the LLM cannot choose another owner.
    The returned list is registered by ``NativeToolProvider``.
    """

    document_repository = DocumentRepository(db=db)
    chunk_repository = DocumentChunkRepository(db=db)
    conversation_repository = ConversationRepository(db=db)
    message_repository = MessageRepository(db=db)

    embedder = GeminiEmbedder()
    semantic_retriever = SemanticRetriever(
        repository=chunk_repository,
        embedder=embedder,
    )
    bm25_retriever = BM25Retriever(repository=chunk_repository)
    hybrid_retriever = HybridRetriever(
        semantic_retriever=semantic_retriever,
        bm25_retriever=bm25_retriever,
    )
    rag_service = RAGService(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        retriever=hybrid_retriever,
        reranker=CrossEncoderReranker(),
    )

    return [
        DocumentSearchTool(
            rag_service=rag_service,
            user_id=str(user_id),
        ),
        WorkspaceStatsTool(
            document_repository=document_repository,
            chunk_repository=chunk_repository,
            conversation_repository=conversation_repository,
            message_repository=message_repository,
            user_id=user_id,
        ),
        WebSearchTool(
            search_service=WebSearchService(
                api_key=settings.TAVILY_API_KEY,
            )
        ),
    ]


# This provider creates local application tools and removes any tools that the
# current user's availability rule does not permit.
class NativeToolProvider(ToolProvider):
    """Build built-in tools and remove any that the user may not access."""

    name = "native"

    # The optional builder keeps production construction unchanged while making
    # permission behavior easy to test without loading RAG dependencies.
    def __init__(
        self,
        db: Session,
        availability_resolver: ToolAvailabilityResolver,
        tool_builder: Callable[
            [Session, UUID],
            Sequence[Any],
        ] = build_native_tools,
    ) -> None:
        self.db = db  # Request session used by native repositories.
        self.availability_resolver = availability_resolver  # Per-user rules.
        self.tool_builder = tool_builder  # Builds native tool instances.

    # Native tools need no network discovery, but use the shared async provider
    # contract so the unified factory can treat every provider the same way.
    async def get_tools(self, user_id: UUID) -> list[Any]:
        """Return built-in tools allowed by ``user_id``'s availability rule."""

        availability = await self.availability_resolver.resolve(user_id)
        tools = self.tool_builder(self.db, user_id)
        return [
            tool
            for tool in tools
            if availability.allows_native_tool(tool.name)
        ]
