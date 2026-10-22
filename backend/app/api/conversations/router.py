"""Conversation and chat HTTP endpoints.

The router checks JWT ownership, then calls ``ChatService`` for conversation
storage and LangGraph execution. ChatService connects this API layer to the
selected user LLM, the unified tool registry, and message repositories.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.conversations.schemas import (
    CreateConversationRequest,
    ConversationResponse,
    MessageResponse,
    RenameConversationRequest,
    SendMessageRequest
)
from app.database.session import get_db
from app.repositories.conversation_repository import (
    ConversationRepository,
)
from app.repositories.message_repository import (
    MessageRepository,
)
from app.services.chat_service import ChatService

router = APIRouter(
    prefix="/api/conversations",
    tags=["Conversations"],
)

from fastapi.responses import StreamingResponse
import asyncio
from app.services.gemini_service import generate_stream_response

from app.core.dependencies import (
    get_current_user,
)

from app.models.user import User
from app.llm.base import LLMProviderError

def get_chat_service(
    db: Session = Depends(get_db),
) -> ChatService:
    """Build ChatService with repositories that share this request's session."""
    return ChatService(
        conversation_repository=ConversationRepository(db),
        message_repository=MessageRepository(db),
    )


# Development-only sample generator retained for the commented stream test.
async def generate_stream():
    """Yield sample words slowly; this is not used by production chat routes."""
    words = ["Hello", "world", "this", "is", "a", "streaming", "response"]

    for word in words:
        await asyncio.sleep(1)
        yield word



@router.get(
    "",
    response_model=list[ConversationResponse],
)
def list_conversations(
    current_user: User = Depends(
        get_current_user
    ),
    service: ChatService = Depends(get_chat_service),
):
    """Return conversations that belong to the authenticated user."""
    return service.list_conversations(
        current_user.id
    )


@router.post(
    "",
    response_model=ConversationResponse,
)
def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(
        get_current_user
    ),
    service: ChatService = Depends(get_chat_service),
):
    """Create a conversation owned by the authenticated user."""
    return service.create_conversation(
        user_id=current_user.id,
        title=request.title,
        mode=request.mode.value,
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def rename_conversation(
    conversation_id: UUID,
    request: RenameConversationRequest,
    current_user: User = Depends(
        get_current_user
    ),
    service: ChatService = Depends(get_chat_service),
):
    """Rename a conversation after ChatService verifies its owner."""
    return service.rename_conversation(
        user=current_user,
        conversation_id=conversation_id,
        title=request.title,
    )


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(
        get_current_user
    ),
    service: ChatService = Depends(get_chat_service),
):
    """Delete one conversation only when it belongs to the current user."""
    conversation = service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized",
        )

    deleted = service.delete_conversation(
        conversation_id
    )

    return {"success": True}


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
def get_messages(
    conversation_id: UUID,
    current_user: User = Depends(
        get_current_user
    ),
    service: ChatService = Depends(get_chat_service),
):
    """Return stored messages after checking conversation ownership."""
    conversation = service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized",
        )

    return service.get_messages(
        conversation_id
    )



# This async endpoint propagates awaiting from HTTP through the chat service to
# LangGraph, which is required when the selected tool is an MCP tool.
@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
)
async def send_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    current_user: User = Depends(
        get_current_user
    ),
    service: ChatService = Depends(get_chat_service),
):
    """Run one asynchronous LangGraph turn and return the saved answer."""
    conversation = service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized",
        )

    try:
        return await service.send_message(
            conversation_id=conversation_id,
            user_message=request.content,
        )
    except LLMProviderError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# This endpoint passes the service's async generator to StreamingResponse so
# MCP calls finish safely before the completed response chunk is emitted.
@router.post(
    "/{conversation_id}/messages/stream",
    response_class=StreamingResponse,
)
async def send_message_stream(
    conversation_id: UUID,
    request: SendMessageRequest,
    current_user: User = Depends(
        get_current_user
    ),
    service: ChatService = Depends(get_chat_service),
):
    """Return ChatService's async response generator as a plain-text stream."""
    conversation = service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized",
        )

    # Validate before StreamingResponse sends HTTP headers. This lets the
    # browser receive a useful JSON error rather than a broken 200 stream.
    try:
        service.require_configured_llm(user_id=current_user.id)
    except LLMProviderError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # STREAMING: Create generator that yields chunks of AI response
    # StreamingResponse sends each chunk to frontend as it arrives
    return StreamingResponse(
        service.send_message_stream(
            conversation_id=conversation_id,
            user_message=request.content,
        ),
        media_type="text/plain",  # STREAMING: Sends plain text chunks
    )




# @router.get("/gemini-stream-test")
# async def gemini_stream_test():

#     prompt = "Explain Java Streams in 10 sentences"

#     return StreamingResponse(
#         generate_stream_response(prompt),
#         media_type="text/plain"
#     )


# @router.get("/stream-test")
# async def stream_test():

#     return StreamingResponse(
#         generate_stream(),
#         media_type="text/plain"
#     )
