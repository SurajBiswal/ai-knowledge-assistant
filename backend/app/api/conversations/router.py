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


def get_chat_service(
    db: Session = Depends(get_db),
) -> ChatService:
    return ChatService(
        conversation_repository=ConversationRepository(db),
        message_repository=MessageRepository(db),
    )


# TEMP USER
# replaced by JWT user in Week 4
DEMO_USER_ID = UUID(
    "11111111-1111-1111-1111-111111111111"
)


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
    service: ChatService = Depends(get_chat_service),
):
    return service.list_conversations(
        DEMO_USER_ID
    )


@router.post(
    "",
    response_model=ConversationResponse,
)
def create_conversation(
    request: CreateConversationRequest,
    service: ChatService = Depends(get_chat_service),
):
    return service.create_conversation(
        user_id=DEMO_USER_ID,
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