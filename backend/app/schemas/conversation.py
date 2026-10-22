"""Define older conversation data shapes kept for compatibility.

These Pydantic classes describe the fields needed to create a conversation
and the fields returned for a stored conversation. The active conversation
routes currently use ``app.api.conversations.schemas`` instead, so this file
is not part of the main request flow at present.

Main connections:
- Mirrors data stored by the ``Conversation`` database model.
- Kept separate from database code so values can be validated safely.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """Validate the title supplied when a conversation is created."""

    title: str = Field(
        min_length=1,
        max_length=500,
    )


class ConversationResponse(BaseModel):
    """Describe conversation data that can be returned to an API caller.

    ``from_attributes`` lets Pydantic read these values directly from a
    SQLAlchemy ``Conversation`` object instead of requiring a dictionary.
    """

    # These identifiers connect the conversation to its database row and owner.
    id: UUID
    user_id: UUID

    # These values describe how the conversation appears and behaves in chat.
    title: str
    mode: str

    # These timestamps tell clients when the row was created and last changed.
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow responses to be built from ORM model attributes."""

        from_attributes = True
