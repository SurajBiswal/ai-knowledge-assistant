from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationMode(str, Enum):
    CHAT = "chat"
    RAG = "rag"
    RESEARCH = "research"


class CreateConversationRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=500,
    )

    mode: ConversationMode = ConversationMode.CHAT


class ConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    content: str = Field(
        min_length=1,
    )


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    token_count: int
    sources: list
    created_at: datetime

    class Config:
        from_attributes = True