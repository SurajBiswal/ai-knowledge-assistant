"""Define older message data shapes kept for compatibility.

The classes in this file validate a message's author role and text, and
describe the fields returned for a saved message. The active conversation API
currently uses ``app.api.conversations.schemas`` instead of these definitions.

Main connections:
- Mirrors data stored by the ``Message`` database model.
- Keeps request and response validation separate from database operations.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """List the allowed authors of a stored chat message."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageCreate(BaseModel):
    """Validate the author role and text for a new message."""

    role: MessageRole
    content: str = Field(
        min_length=1,
    )


class MessageResponse(BaseModel):
    """Describe message data that can be returned to an API caller.

    ``from_attributes`` lets this response read values directly from the
    SQLAlchemy ``Message`` object produced by the repository layer.
    """

    # These identifiers locate the message and its parent conversation.
    id: UUID
    conversation_id: UUID

    # These fields contain the author, visible text, and optional source data.
    role: str
    content: str
    token_count: int
    sources: list

    # The creation time is shown to clients and used to order messages.
    created_at: datetime

    class Config:
        """Allow responses to be built from ORM model attributes."""

        from_attributes = True
