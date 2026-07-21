from typing import TypedDict
from app.rag.retriever import RetrievedChunk


class ChatState(TypedDict):
    conversation_id: str                  # Current conversation ID
    query: str                            # Current user query
    messages: list                        # Conversation history
    retrieved_docs: list[RetrievedChunk]  # Retrieved RAG chunks
    response: str                         # AI response