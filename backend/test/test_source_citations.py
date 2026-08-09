from uuid import uuid4

from app.rag.citation_builder import CitationBuilder
from app.rag.retriever import RetrievedChunk


def print_separator(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


builder = CitationBuilder()


# ---------------------------------------------------------
# Test 1
# Multiple retrieved chunks
# ---------------------------------------------------------

print_separator("TEST 1 - Multiple Retrieved Chunks")

chunks = [
    RetrievedChunk(
        document_id=uuid4(),
        chunk_index=0,
        chunk_text="Spring Boot is a Java framework.",
        metadata={
            "document_id": "doc-1",
            "filename": "Spring_Boot_Guide.pdf",
            "page": 3,
        },
        cosine_distance=0.08,
    ),
    RetrievedChunk(
        document_id=uuid4(),
        chunk_index=1,
        chunk_text="Constructor Injection is recommended.",
        metadata={
            "document_id": "doc-1",
            "filename": "Spring_Boot_Guide.pdf",
            "page": 3,
        },
        cosine_distance=0.12,
    ),
    RetrievedChunk(
        document_id=uuid4(),
        chunk_index=2,
        chunk_text="JWT Authentication secures APIs.",
        metadata={
            "document_id": "doc-2",
            "filename": "Security_Guide.pdf",
            "page": 10,
        },
        cosine_distance=0.18,
    ),
]

citations = builder.build_citations(chunks)

print("Generated Citations:\n")

for citation in citations:
    print(citation)

assert len(citations) == 2

print("\nPASS - Duplicate document references removed")


# ---------------------------------------------------------
# Test 2
# Empty retrieval
# ---------------------------------------------------------

print_separator("TEST 2 - Empty Retrieval")

citations = builder.build_citations([])

print(citations)

assert citations == []

print("\nPASS - Empty retrieval handled")


# ---------------------------------------------------------
# Test 3
# Missing metadata
# ---------------------------------------------------------

print_separator("TEST 3 - Missing Metadata")

chunks = [
    RetrievedChunk(
        document_id=uuid4(),
        chunk_index=5,
        chunk_text="Chunk with missing metadata.",
        metadata={},
        cosine_distance=0.25,
    )
]

citations = builder.build_citations(chunks)

print(citations)

assert len(citations) == 1

print("\nPASS - Missing metadata handled")


# ---------------------------------------------------------
# Test 4
# Citation formatting
# ---------------------------------------------------------

print_separator("TEST 4 - Citation Formatting")

formatted = builder.format_citations(
    [
        {
            "document_id": "doc-1",
            "filename": "Spring_Boot_Guide.pdf",
            "page": 3,
            "chunk_index": 0,
        },
        {
            "document_id": "doc-2",
            "filename": "Security_Guide.pdf",
            "page": 10,
            "chunk_index": 2,
        },
    ]
)

print(formatted)

assert "Spring_Boot_Guide.pdf" in formatted
assert "Security_Guide.pdf" in formatted

print("\nPASS - Citation formatting")


# ---------------------------------------------------------
# Test 5
# Final response payload
# ---------------------------------------------------------

print_separator("TEST 5 - Final Response")

sources = builder.build_citations(chunks)

response = {
    "response": (
        "Constructor Injection is recommended because it "
        "supports immutable dependencies."
    ),
    "sources": sources,
}

print(response)

assert "response" in response
assert "sources" in response

print("\nPASS - Final response contains sources")


# ---------------------------------------------------------
# ALL TESTS PASSED
# ---------------------------------------------------------

print_separator("ALL SOURCE CITATION TESTS PASSED")