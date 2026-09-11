from unittest.mock import Mock

from app.rag.retriever import RetrievedChunk
from app.tools.document_search import DocumentSearchTool
from app.tools.schemas import SearchDocumentsInput


def make_chunk(
    document_id,
    chunk_index,
    text,
    filename,
    score,
):
    return RetrievedChunk(
        document_id=document_id,
        chunk_index=chunk_index,
        chunk_text=text,
        metadata={"filename": filename},
        score=float(score),
    )


def test_search_documents_tool_uses_rag_service():
    rag_service = Mock()

    rag_service.retrieve.return_value = [
        make_chunk(
            "doc-1",
            4,
            "JWT is a compact token format used for claims.",
            "authentication.pdf",
            0.91,
        ),
        make_chunk(
            "doc-2",
            2,
            "JWTs can carry signed claims between parties.",
            "security.pdf",
            0.84,
        ),
    ]

    tool = DocumentSearchTool(rag_service)

    result = tool.execute(
        SearchDocumentsInput(
            query="How does JWT authentication work?",
            top_k=2,
        )
    )

    rag_service.retrieve.assert_called_once_with(
        question="How does JWT authentication work?",
        top_k=2,
    )

    assert len(result.results) == 2

    assert result.results[0].document == "authentication.pdf"
    assert result.results[0].chunk_index == 4
    assert result.results[0].content.startswith("JWT is")
    assert result.results[0].score == 0.91


def test_search_documents_tool_validates_input():
    rag_service = Mock()
    tool = DocumentSearchTool(rag_service)

    try:
        tool.execute(
            {
                "query": "",
                "top_k": 5,
            }
        )
    except Exception:
        pass
    else:
        raise AssertionError("Invalid input should be rejected.")


def test_search_documents_tool_returns_empty_results():
    rag_service = Mock()
    rag_service.retrieve.return_value = []

    tool = DocumentSearchTool(rag_service)

    result = tool.execute(
        {
            "query": "query with no matching documents",
            "top_k": 5,
        }
    )

    assert result.results == []
