"""Response shapes for document upload, listing, and deletion endpoints.

These models keep the document API response stable while the underlying data
comes from SQLAlchemy Document objects and DocumentService operations.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Public information about one document uploaded by the user."""

    id: UUID
    filename: str
    file_type: str
    file_size: int
    status: str
    uploaded_at: datetime

    model_config = {
        "from_attributes": True
    }


class DeleteDocumentResponse(BaseModel):
    """Confirmation message returned after a document is deleted."""

    message: str
