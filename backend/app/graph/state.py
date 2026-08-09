from typing import TypedDict, Any

from app.rag.retriever import RetrievedChunk


class ChatState(TypedDict):
    """
    Shared state passed between LangGraph nodes.

    Each node reads from and/or writes to this state as the
    conversation progresses through the graph.
    """

    # Current conversation information
    conversation_id: str
    query: str
    messages: list

    # Retrieval stage output
    retrieved_docs: list[RetrievedChunk]

    # Citation Builder output
    sources: list[dict[str, Any]]

    # Context Builder output
    context: str

    # Prompt Builder output
    prompt: str

    # Final LLM response
    response: str