from uuid import uuid4

from app.rag.context_builder import ContextBuilder
from app.rag.retriever import RetrievedChunk


def print_separator(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


builder = ContextBuilder()


# ---------------------------------------------------------
# Test 1
# Multiple retrieved chunks
# ---------------------------------------------------------

print_separator("TEST 1 - Multiple Retrieved Chunks")

chunks = [
    RetrievedChunk(
        document_id=uuid4(),
        chunk_index=0,
        chunk_text="Spring Boot is a Java framework for building applications.",
        metadata={
            "filename": "Spring_Boot_Guide.pdf",
            "page": 3,
        },
        cosine_distance=0.11,
    ),
    RetrievedChunk(
        document_id=uuid4(),
        chunk_index=1,
        chunk_text="Dependency Injection allows Spring to manage object creation.",
        metadata={
            "filename": "Spring_Boot_Guide.pdf",
            "page": 5,
        },
        cosine_distance=0.18,
    ),
    RetrievedChunk(
        document_id=uuid4(),
        chunk_index=2,
        chunk_text="Constructor Injection is generally preferred over field injection.",
        metadata={
            "filename": "Spring_Boot_Guide.pdf",
            "page": 6,
        },
        cosine_distance=0.23,
    ),
]

context = builder.build_context(chunks)

print(context)


# ---------------------------------------------------------
# Test 2
# Single retrieved chunk
# ---------------------------------------------------------

print_separator("TEST 2 - Single Retrieved Chunk")

single_chunk = [
    RetrievedChunk(
        document_id=uuid4(),
        chunk_index=5,
        chunk_text="JWT tokens are digitally signed.",
        metadata={
            "filename": "Security.pdf",
            "page": 10,
        },
        cosine_distance=0.08,
    )
]

context = builder.build_context(single_chunk)

print(context)


# ---------------------------------------------------------
# Test 3
# Empty retrieval result
# ---------------------------------------------------------

print_separator("TEST 3 - Empty Retrieval")

context = builder.build_context([])

print(repr(context))


# ---------------------------------------------------------
# Test 4
# Missing metadata
# ---------------------------------------------------------

print_separator("TEST 4 - Missing Metadata")

missing_metadata = [
    RetrievedChunk(
        document_id=uuid4(),
        chunk_index=7,
        chunk_text="Metadata is unavailable for this chunk.",
        metadata={},
        cosine_distance=0.32,
    )
]

context = builder.build_context(missing_metadata)

print(context)


# ---------------------------------------------------------
# Test 5
# Verify retrieval order
# ---------------------------------------------------------

print_separator("TEST 5 - Retrieval Order")

ordered_chunks = [
    RetrievedChunk(
        document_id=uuid4(),
        chunk_index=9,
        chunk_text="FIRST CHUNK",
        metadata={
            "filename": "order.pdf",
            "page": 1,
        },
        cosine_distance=0.05,
    ),
    RetrievedChunk(
        document_id=uuid4(),
        chunk_index=2,
        chunk_text="SECOND CHUNK",
        metadata={
            "filename": "order.pdf",
            "page": 2,
        },
        cosine_distance=0.12,
    ),
    RetrievedChunk(
        document_id=uuid4(),
        chunk_index=6,
        chunk_text="THIRD CHUNK",
        metadata={
            "filename": "order.pdf",
            "page": 3,
        },
        cosine_distance=0.20,
    ),
]

context = builder.build_context(ordered_chunks)

print(context)