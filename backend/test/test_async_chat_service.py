from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from app.services import chat_service as chat_service_module
from app.services.chat_service import ChatService


# This helper creates an isolated service whose repositories behave like the
# real persistence layer but do not require a database for async-flow tests.
def make_chat_service():
    user_id = uuid4()
    conversation_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id=user_id,
        title="Existing conversation",
    )
    conversation_repository = Mock()
    conversation_repository.db = Mock()
    conversation_repository.get_by_id.return_value = conversation
    message_repository = Mock()
    message_repository.get_last_n_messages.return_value = []
    service = ChatService(
        conversation_repository=conversation_repository,
        message_repository=message_repository,
    )
    service.require_configured_llm = Mock()
    return service, message_repository, conversation


# This test proves the ordinary chat method awaits LangGraph's async execution
# before it persists and returns the assistant message.
def test_send_message_awaits_graph_ainvoke(monkeypatch) -> None:
    service, message_repository, conversation = make_chat_service()
    assistant_message = SimpleNamespace(content="Async answer")
    message_repository.create.side_effect = [
        SimpleNamespace(content="Question"),
        assistant_message,
    ]
    graph = SimpleNamespace(
        ainvoke=AsyncMock(
            return_value={"response": "Async answer", "sources": []}
        )
    )
    monkeypatch.setattr(
        chat_service_module,
        "create_graph",
        Mock(return_value=graph),
    )

    result = asyncio.run(
        service.send_message(
            conversation_id=conversation.id,
            user_message="Question",
        )
    )

    assert result is assistant_message
    graph.ainvoke.assert_awaited_once()
    message_repository.create.assert_called_with(
        conversation_id=conversation.id,
        role="assistant",
        content="Async answer",
        sources=[],
    )


# This coroutine consumes the service's async generator exactly as FastAPI's
# StreamingResponse does when it sends response chunks to the browser.
async def collect_stream(service, conversation_id):
    return [
        chunk
        async for chunk in service.send_message_stream(
            conversation_id=conversation_id,
            user_message="Question",
        )
    ]


# This test proves the streaming chat path also awaits the asynchronous graph
# and persists the assistant response after its response chunk is consumed.
def test_send_message_stream_awaits_graph_ainvoke(monkeypatch) -> None:
    service, message_repository, conversation = make_chat_service()
    sources = [
        {
            "document_id": "doc-1",
            "filename": "story.pdf",
            "page": 7,
            "chunk_index": 13,
            "excerpt": "Arin rang the bell.",
        }
    ]
    graph = SimpleNamespace(
        ainvoke=AsyncMock(
            return_value={"response": "Streamed answer", "sources": sources}
        )
    )
    monkeypatch.setattr(
        chat_service_module,
        "create_graph",
        Mock(return_value=graph),
    )

    chunks = asyncio.run(collect_stream(service, conversation.id))

    assert chunks == ["Streamed answer"]
    graph.ainvoke.assert_awaited_once()
    message_repository.create.assert_called_with(
        conversation_id=conversation.id,
        role="assistant",
        content="Streamed answer",
        sources=sources,
    )
