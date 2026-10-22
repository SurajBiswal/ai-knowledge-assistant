"""Business logic for uploading, indexing, listing, and deleting documents.

The document API calls this service. It validates files, stores them under the
upload directory, saves Document metadata through repositories, and asks
``RAGService`` to extract, chunk, embed, and index their text.
"""

from pathlib import Path
from uuid import uuid4, UUID
from fastapi import HTTPException, UploadFile, status

from app.models.document import Document
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.services.rag_service import RAGService
# Directory where accepted uploads are stored using generated filenames.
UPLOAD_DIR = Path("uploads")

class DocumentService:
    """Coordinate filesystem work, document persistence, and RAG indexing."""

    # Only formats supported by DocumentExtractor may be uploaded.
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
    # Limit memory use and storage by rejecting files larger than 20 MB.
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

    def __init__(self, document_repository: DocumentRepository, chunk_repository: DocumentChunkRepository):
        """Store repositories and build the RAG service used during uploads."""
        self.document_repository = document_repository
        self.chunk_repository = chunk_repository
        self.rag_service = RAGService(
            document_repository=document_repository,
            chunk_repository=chunk_repository,
            # retriever=None  # Placeholder, replace with actual retriever if needed
        )

    def _create_upload_directory(self) -> None:
        """Create the upload directory when it does not already exist."""
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Return a random server filename while preserving the file extension."""
        extension = original_filename.rsplit(".", 1)[-1].lower()
        return f"{uuid4()}.{extension}"

    def upload_document(
        self,
        current_user: User,
        file: UploadFile,
    ) -> Document:
        """Validate, save, index, and return one authenticated user's upload."""

        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file selected.",
            )

        if "." not in file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file name.",
            )

        # Validate extension
        extension = file.filename.rsplit(".", 1)[-1].lower()

        if extension not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}",
            )

        # Read file bytes
        file_bytes = file.file.read()
        file.file.close()  # Close the file after reading
        file_size = len(file_bytes)

        # Validate size
        if file_size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds the maximum limit of 20 MB.",
            )

        # Create uploads directory if needed
        self._create_upload_directory()

        # Generate unique filename
        unique_filename = self._generate_unique_filename(file.filename)

        file_path = UPLOAD_DIR / unique_filename

        # Save file
        try:
            file_path.write_bytes(file_bytes)
        except OSError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded file.",
            )

        # Create ORM object
        document = Document(
            user_id=current_user.id,
            filename=file.filename,
            file_path=str(file_path),
            file_type=extension,
            file_size=file_size,
            status="uploaded",
        )

        try:
            document = self.document_repository.create(document)
        except Exception as e:
            if file_path.exists():
                file_path.unlink()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save document metadata.",
            ) from e
        
        try:
            self.rag_service.index_document(document)
        except Exception as e:
            document.status = "error"
            self.document_repository.update(document)

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process document: {e}",
            ) from e
        
        return document
    
    
    def list_documents(
        self,
        current_user: User,
    ) -> list[Document]:
        """Return the current user's documents with newest uploads first."""
        return self.document_repository.list_by_user(current_user.id)
    

    def delete_document(
        self,
        current_user: User,
        document_id: UUID,
    ) -> None:
        """Delete an owned document from both the filesystem and database."""
        document = self.document_repository.get_by_id_and_user(
            document_id=document_id,
            user_id=current_user.id,
        )
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )

        # Delete the file from the filesystem
        file_path = Path(document.file_path)
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete the file from the server.",
            )

        # Delete the record from the database
        self.document_repository.delete(document)
