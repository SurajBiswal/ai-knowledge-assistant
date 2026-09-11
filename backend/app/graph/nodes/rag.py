from sqlalchemy.orm import Session

from app.graph.state import ChatState

from app.rag.bm25_retriever import BM25Retriever
from app.rag.citation_builder import CitationBuilder
from app.rag.cross_encoder_reranker import CrossEncoderReranker
from app.rag.embedder import GeminiEmbedder
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.retriever import SemanticRetriever

from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)

from app.repositories.document_repository import (
    DocumentRepository,
)

from app.services.rag_service import RAGService


# Factory that creates a RAG node with its dependencies.
def create_rag_node(db: Session):

    # ---------------------------------------------------------
    # 1. Repositories
    # ---------------------------------------------------------

    chunk_repository = DocumentChunkRepository(
        db=db
    )

    document_repository = DocumentRepository(
        db=db
    )

    # ---------------------------------------------------------
    # 2. Semantic Retriever
    # ---------------------------------------------------------

    embedder = GeminiEmbedder()

    semantic_retriever = SemanticRetriever(
        repository=chunk_repository,
        embedder=embedder,
    )

    # ---------------------------------------------------------
    # 3. BM25 Retriever
    # ---------------------------------------------------------

    bm25_retriever = BM25Retriever(
        repository=chunk_repository,
    )

    # ---------------------------------------------------------
    # 4. Hybrid Retriever
    #
    # Semantic + BM25
    #        ↓
    #   Candidate chunks
    # ---------------------------------------------------------

    retriever = HybridRetriever(
        semantic_retriever=semantic_retriever,
        bm25_retriever=bm25_retriever,
    )

    # ---------------------------------------------------------
    # 5. Cross Encoder Reranker
    #
    # Candidate chunks
    #        ↓
    # Cross Encoder
    #        ↓
    # Final ranked chunks
    # ---------------------------------------------------------

    reranker = CrossEncoderReranker()

    # ---------------------------------------------------------
    # 6. RAG Service
    #
    # RAGService now owns:
    #
    # HybridRetriever
    #       ↓
    # CrossEncoderReranker
    # ---------------------------------------------------------

    rag_service = RAGService(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        retriever=retriever,
        reranker=reranker,
    )

    # ---------------------------------------------------------
    # 7. Citation Builder
    # ---------------------------------------------------------

    citation_builder = CitationBuilder()

    # ---------------------------------------------------------
    # 8. LangGraph RAG Node
    # ---------------------------------------------------------

    def rag_node(state: ChatState) -> ChatState:

        query = state["query"]
        user_id = state["user_id"]

        # -----------------------------------------------------
        # Retrieval
        #
        # Question
        #     ↓
        # HybridRetriever
        #     ↓
        # Candidate chunks
        #     ↓
        # CrossEncoderReranker
        #     ↓
        # Final chunks
        # -----------------------------------------------------

        retrieved_docs = rag_service.retrieve(
            question=query,
            user_id=user_id,
            top_k=5,
        )

        # -----------------------------------------------------
        # Context construction
        # -----------------------------------------------------

        context = rag_service.build_context(
            retrieved_docs
        )

        # -----------------------------------------------------
        # Citation generation
        # -----------------------------------------------------

        sources = citation_builder.build_citations(
            retrieved_docs
        )

        # -----------------------------------------------------
        # Return graph state
        # -----------------------------------------------------

        return {
            "retrieved_docs": retrieved_docs,
            "context": context,
            "sources": sources,
        }

    return rag_node