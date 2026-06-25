from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.conversations.schemas import (
    CreateConversationRequest,
    ConversationResponse,
    MessageResponse,
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

def get_chat_service(
    db: Session = Depends(get_db),
) -> ChatService:
    return ChatService(
        conversation_repository=ConversationRepository(db),
        message_repository=MessageRepository(db),
    )


# TEMP USER
# replaced by JWT user in Week 4
# DEMO_USER_ID = UUID(
#     "11111111-1111-1111-1111-111111111111"
# )


async def generate_stream():
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
    return service.create_conversation(
        user_id=current_user.id,
        title=request.title,
        mode=request.mode.value,
    )


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    service: ChatService = Depends(get_chat_service),
):
    deleted = service.delete_conversation(
        conversation_id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return {"success": True}


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
def get_messages(
    conversation_id: UUID,
    service: ChatService = Depends(get_chat_service),
):
    return service.get_messages(
        conversation_id
    )



@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
)
def send_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    service: ChatService = Depends(get_chat_service),
):
    return service.send_message(
        conversation_id=conversation_id,
        user_message=request.content,
    )


# STREAMING: New endpoint for streaming responses
# Frontend calls this instead of /messages to get real-time text streaming
@router.post(
    "/{conversation_id}/messages/stream",
    response_class=StreamingResponse,
)
async def send_message_stream(
    conversation_id: UUID,
    request: SendMessageRequest,
    service: ChatService = Depends(get_chat_service),
):
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