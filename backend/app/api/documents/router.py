from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.core.dependencies import (
    get_current_user,
)

from app.models.user import User

from app.repositories.document_repository import (
    DocumentRepository,
)

from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)

from app.services.document_service import (
    DocumentService,
)

from app.api.documents.schemas import (
    DocumentResponse,
    DeleteDocumentResponse,
)


router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"],
)


def get_document_service(
    db: Session = Depends(get_db),
) -> DocumentService:
    return DocumentService(
        DocumentRepository(db),
        DocumentChunkRepository(db)
    )


@router.post(
    "/upload",
    response_model=DocumentResponse,
)
def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(
        get_document_service,
    ),
):
    return service.upload_document(
        current_user=current_user,
        file=file,
    )


@router.get(
    "",
    response_model=list[DocumentResponse],
)
def list_documents(
    current_user: User = Depends(
        get_current_user,
    ),
    service: DocumentService = Depends(
        get_document_service,
    ),
):
    return service.list_documents(
        current_user=current_user,
    )


@router.delete(
    "/{document_id}",
    response_model=DeleteDocumentResponse,
)
def delete_document(
    document_id: UUID,
    current_user: User = Depends(
        get_current_user,
    ),
    service: DocumentService = Depends(
        get_document_service,
    ),
):
    service.delete_document(
        current_user=current_user,
        document_id=document_id,
    )

    return {
        "message": "Document deleted successfully."
    }