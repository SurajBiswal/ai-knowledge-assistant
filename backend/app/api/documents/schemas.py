from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
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
    message: str