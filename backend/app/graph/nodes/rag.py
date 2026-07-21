from sqlalchemy.orm import Session

from app.graph.state import ChatState
from app.rag.embedder import GeminiEmbedder
from app.rag.retriever import SemanticRetriever
from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)

# Factory that creates a RAG node with its dependencies.
def create_rag_node(db: Session):

    repository = DocumentChunkRepository(db=db)

    embedder = GeminiEmbedder()

    retriever = SemanticRetriever(
        repository=repository,
        embedder=embedder,
    )
    # LangGraph RAG node.
    def rag_node(state: ChatState) -> ChatState:

        query = state["query"]

        retrieved_docs = retriever.retrieve(
            question=query,
            top_k=5,
        )

        return {
            "retrieved_docs": retrieved_docs,
        }

    return rag_node