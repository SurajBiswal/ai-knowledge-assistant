from sqlalchemy.orm import Session

from app.graph.state import ChatState
from app.rag.bm25_retriever import BM25Retriever
from app.rag.citation_builder import CitationBuilder
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

    chunk_repository = DocumentChunkRepository(db=db)
    document_repository = DocumentRepository(db=db)

    # Semantic retrieval dependencies
    embedder = GeminiEmbedder()

    semantic_retriever = SemanticRetriever(
        repository=chunk_repository,
        embedder=embedder,
    )

    # BM25 lexical retriever
    bm25_retriever = BM25Retriever(
        repository=chunk_repository,
    )

    # Hybrid retrieval combines semantic + BM25 retrieval.
    retriever = HybridRetriever(
        semantic_retriever=semantic_retriever,
        bm25_retriever=bm25_retriever,
    )

    rag_service = RAGService(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        retriever=retriever,
    )

    citation_builder = CitationBuilder()

    # LangGraph RAG node.
    def rag_node(state: ChatState) -> ChatState:

        query = state["query"]

        retrieved_docs = rag_service.retrieve(
            question=query,
            top_k=5,
        )

        context = rag_service.build_context(
            retrieved_docs
        )

        # Step 3: Build source citations
        sources = citation_builder.build_citations(
            retrieved_docs
        )

        return {
            "retrieved_docs": retrieved_docs,
            "context": context,
            "sources": sources
        }

    return rag_node