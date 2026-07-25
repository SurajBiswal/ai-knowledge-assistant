from app.database.session import SessionLocal
from app.rag.embedder import GeminiEmbedder
from app.rag.query_rewriter import QueryRewriter
from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)


def print_results(title, results):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

    if not results:
        print("No chunks found.")
        return

    for i, (chunk, distance) in enumerate(results, start=1):
        print(f"\nResult {i}")
        print(f"Distance : {distance:.4f}")
        print(f"Document : {chunk.document_id}")
        print(f"Chunk    : {chunk.chunk_index}")
        print("-" * 80)
        print(chunk.chunk_text[:500])
        print("-" * 80)


def main():

    db = SessionLocal()

    repository = DocumentChunkRepository(db)
    embedder = GeminiEmbedder()
    rewriter = QueryRewriter()

    question = input("Question: ").strip()

    rewritten_query = rewriter.rewrite_query(question)

    print("\nOriginal Query:")
    print(question)

    print("\nRewritten Query:")
    print(rewritten_query)

    print("\nGenerating embeddings...")

    original_embedding = embedder.generate_embedding(question)

    rewritten_embedding = embedder.generate_embedding(
        rewritten_query
    )

    original_results = repository.search_similar(
        query_embedding=original_embedding,
        top_k=5,
    )

    rewritten_results = repository.search_similar(
        query_embedding=rewritten_embedding,
        top_k=5,
    )

    print_results(
        "Results using ORIGINAL query",
        original_results,
    )

    print_results(
        "Results using REWRITTEN query",
        rewritten_results,
    )

    db.close()


if __name__ == "__main__":
    main()