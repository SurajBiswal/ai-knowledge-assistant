"""Request and response shapes for conversations and chat messages.

The conversation router uses these models to validate frontend input and turn
SQLAlchemy Conversation and Message objects into predictable JSON responses.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationMode(str, Enum):
    """Allowed conversation modes accepted when a conversation is created."""

    CHAT = "chat"
    RAG = "rag"
    RESEARCH = "research"


class CreateConversationRequest(BaseModel):
    """Title and mode supplied by the frontend for a new conversation."""

    title: str = Field(
        min_length=1,
        max_length=500,
    )

    mode: ConversationMode = ConversationMode.CHAT


class ConversationResponse(BaseModel):
    """Conversation fields returned to the frontend."""

    id: UUID
    user_id: UUID
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy model objects."""

        from_attributes = True


class RenameConversationRequest(BaseModel):
    """New title supplied when the user renames a conversation."""

    title: str = Field(
        min_length=1,
        max_length=500,
    )


class SendMessageRequest(BaseModel):
    """Text the user wants to send to the assistant."""

    content: str = Field(
        min_length=1,
    )


class MessageResponse(BaseModel):
    """Stored user or assistant message returned by the API."""

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    token_count: int
    sources: list
    created_at: datetime

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy model objects."""

        from_attributes = True
