from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# Pydantic schemas for Conversation

# These schemas define the structure of the data for creating and responding with Conversation objects in the API. 
class ConversationCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=500,
    )

# The ConversationResponse schema includes all the fields of a Conversation, including the id, user_id, title, mode, created_at, and updated_at. 
# The Config class with from_attributes = True allows Pydantic to create a ConversationResponse object from an instance of the Conversation model, which is useful when returning data from the database in API responses.
class ConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True