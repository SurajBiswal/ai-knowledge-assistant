from app.core.dependencies import get_db
from app.rag.bm25_retriever import BM25Retriever
from app.rag.cross_encoder_reranker import CrossEncoderReranker
from app.rag.embedder import GeminiEmbedder
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.retriever import SemanticRetriever
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.services.rag_service import RAGService
from app.tools.document_search import DocumentSearchTool


def build_rag_service(db):
    chunk_repository = DocumentChunkRepository(db=db)
    document_repository = DocumentRepository(db=db)

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

    return RAGService(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        retriever=hybrid_retriever,
        reranker=reranker,
    )


def main():
    # Replace this with the UUID of a real user in your database.
    user_id = "82ff9f42-6ee7-4379-9227-f12f9805adc9"

    db = next(get_db())

    try:
        rag_service = build_rag_service(db)

        tool = DocumentSearchTool(
            rag_service=rag_service,
            user_id=user_id,
        )

        result = tool.execute(
            {
                "query": "What message did the mysterious device reveal?",
                "top_k": 5,
            }
        )

        print("\n=== SEARCH RESULTS ===")

        for index, item in enumerate(result.results, start=1):
            print(f"\n--- Result {index} ---")
            print(f"Document: {item.document}")
            print(f"Chunk:    {item.chunk_index}")
            print(f"Score:    {item.score}")
            print(f"Content:  {item.content[:500]}")

        print(f"\nTotal results: {len(result.results)}")

    finally:
        db.close()


if __name__ == "__main__":
    main()