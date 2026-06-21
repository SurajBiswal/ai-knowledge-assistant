from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

# Pydantic schemas for Message
# These schemas define the structure of the data for creating and responding with Message objects in the API.
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

# The MessageCreate schema includes the role and content fields, which are required when creating a new message. The role field is an enumeration that specifies whether the message is from the user, assistant, or system. The content field is a string that contains the text of the message.
class MessageCreate(BaseModel):
    role: MessageRole
    content: str = Field(
        min_length=1,
    )

# The MessageResponse schema includes all the fields of a Message, including the id, conversation_id, role, content, token_count, sources, and created_at. The Config class with from_attributes = True allows Pydantic to create a MessageResponse object from an instance of the Message model, which is useful when returning data from the database in API responses.
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