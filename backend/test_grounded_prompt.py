"""
Grounded Prompt Validation

This script validates the complete RAG pipeline.

Flow:
Question
    ↓
Query Rewriter
    ↓
Semantic Retriever
    ↓
Context Builder
    ↓
Prompt Builder

It prints:
- Retrieved chunks
- Generated context
- Final grounded prompt

Run:

python backend/test_grounded_prompt.py
"""

from sqlalchemy.orm import Session

from app.database.session import SessionLocal

from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)

from app.rag.embedder import GeminiEmbedder
from app.rag.retriever import SemanticRetriever
from app.rag.context_builder import ContextBuilder
from app.rag.prompt_builder import PromptBuilder


QUESTION = (
    "Who visited the observatory in 2021, "
    "why did he visit, and what conclusion did he reach?"
)


def main() -> None:
    db: Session = SessionLocal()

    try:
        repository = DocumentChunkRepository(db)

        embedder = GeminiEmbedder()

        retriever = SemanticRetriever(
            repository=repository,
            embedder=embedder,
        )

        context_builder = ContextBuilder()

        prompt_builder = PromptBuilder()

        print("=" * 80)
        print("QUESTION")
        print("=" * 80)
        print(QUESTION)

        retrieved_chunks = retriever.retrieve(
            question=QUESTION,
            top_k=5,
        )

        print("\n")
        print("=" * 80)
        print(f"RETRIEVED CHUNKS ({len(retrieved_chunks)})")
        print("=" * 80)

        for index, chunk in enumerate(retrieved_chunks, start=1):
            print(f"\nChunk {index}")
            print("-" * 60)

            print(f"Document ID : {chunk.document_id}")
            print(f"Chunk Index : {chunk.chunk_index}")
            print(f"Similarity  : {chunk.cosine_distance:.6f}")
            print(f"Metadata    : {chunk.metadata}")

            preview = chunk.chunk_text[:300]

            if len(chunk.chunk_text) > 300:
                preview += "..."

            print("\nContent:")
            print(preview)

        context = context_builder.build_context(
            retrieved_chunks
        )

        print("\n")
        print("=" * 80)
        print("GENERATED CONTEXT")
        print("=" * 80)
        print(context)

        prompt = prompt_builder.build_prompt(
            question=QUESTION,
            context=context,
        )

        print("\n")
        print("=" * 80)
        print("FINAL PROMPT SENT TO GEMINI")
        print("=" * 80)
        print(prompt)

        print("\n")
        print("=" * 80)
        print("VALIDATION PASSED")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()