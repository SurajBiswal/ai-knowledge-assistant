from app.database.session import SessionLocal
from app.rag.embedder import GeminiEmbedder
from app.rag.retriever import SemanticRetriever
from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)


def main():

    db = SessionLocal()

    try:
        repository = DocumentChunkRepository(db)
        embedder = GeminiEmbedder()

        retriever = SemanticRetriever(
            repository=repository,
            embedder=embedder,
        )

        question = "How does RecursiveCharacterTextSplitter work?"

        print(f"\nQuestion: {question}\n")

        results = retriever.retrieve(
            question=question,
            top_k=5,
        )

        if not results:
            print("No relevant chunks found.")
            return

        print(f"Retrieved {len(results)} chunk(s):\n")

        for index, chunk in enumerate(results, start=1):

            print(f"Result {index}")

            print(
                f"Cosine Distance: "
                f"{chunk.cosine_distance:.4f}"
            )

            print(
                f"Document ID: "
                f"{chunk.document_id}"
            )

            print(
                f"Chunk Index: "
                f"{chunk.chunk_index}"
            )

            print("Chunk:")

            print(chunk.chunk_text)

            print("-" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()