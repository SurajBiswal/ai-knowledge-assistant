from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings

from app.rag.bm25_retriever import BM25Retriever
from app.rag.cross_encoder_reranker import CrossEncoderReranker
from app.rag.embedder import GeminiEmbedder
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.retriever import SemanticRetriever

from app.repositories.conversation_repository import (
    ConversationRepository,
)
from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)
from app.repositories.document_repository import (
    DocumentRepository,
)
from app.repositories.message_repository import (
    MessageRepository,
)

from app.services.rag_service import RAGService
from app.services.web_search_service import WebSearchService

from app.tools.document_search import DocumentSearchTool
from app.tools.registry import ToolRegistry
from app.tools.web_search import WebSearchTool
from app.tools.workspace_stats import WorkspaceStatsTool


def create_tool_registry(
    db: Session,
    user_id: UUID,
) -> ToolRegistry:
    """
    Create a ToolRegistry for one authenticated user.

    The application supplies user_id from authentication/session context.
    The LLM never supplies or controls user identity.
    """

    # ---------------------------------------------------------
    # Repositories
    # ---------------------------------------------------------

    document_repository = DocumentRepository(
        db=db,
    )

    chunk_repository = DocumentChunkRepository(
        db=db,
    )

    conversation_repository = ConversationRepository(
        db=db,
    )

    message_repository = MessageRepository(
        db=db,
    )

    # ---------------------------------------------------------
    # RAG dependencies
    # ---------------------------------------------------------

    embedder = GeminiEmbedder()

    semantic_retriever = SemanticRetriever(
        repository=chunk_repository,
        embedder=embedder,
    )

    bm25_retriever = BM25Retriever(
        repository=chunk_repository,
    )

    hybrid_retriever = HybridRetriever(
        semantic_retriever=semantic_retriever,
        bm25_retriever=bm25_retriever,
    )

    reranker = CrossEncoderReranker()

    rag_service = RAGService(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        retriever=hybrid_retriever,
        reranker=reranker,
    )

    # ---------------------------------------------------------
    # External services
    # ---------------------------------------------------------

    web_search_service = WebSearchService(
        api_key=settings.TAVILY_API_KEY,
    )

    # ---------------------------------------------------------
    # Tools
    # ---------------------------------------------------------

    document_search_tool = DocumentSearchTool(
        rag_service=rag_service,
        user_id=str(user_id),
    )

    workspace_stats_tool = WorkspaceStatsTool(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        user_id=user_id,
    )

    web_search_tool = WebSearchTool(
        search_service=web_search_service,
    )

    # ---------------------------------------------------------
    # Registry
    # ---------------------------------------------------------

    registry = ToolRegistry()

    registry.register(
        document_search_tool
    )

    registry.register(
        workspace_stats_tool
    )

    registry.register(
        web_search_tool
    )

    return registry