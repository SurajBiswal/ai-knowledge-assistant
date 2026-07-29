from sqlalchemy.orm import Session

from app.graph.state import ChatState
from app.rag.embedder import GeminiEmbedder
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

    embedder = GeminiEmbedder()

    retriever = SemanticRetriever(
        repository=chunk_repository,
        embedder=embedder,
    )

    rag_service = RAGService(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        retriever=retriever,
    )

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

        return {
            "retrieved_docs": retrieved_docs,
            "context": context,
        }

    return rag_node