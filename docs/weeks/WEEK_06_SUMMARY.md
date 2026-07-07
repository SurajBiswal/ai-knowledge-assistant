## Week 6 — Document Upload & Management

- **Current week:** Week 6 (Completed)
- **Current branch:** `suraj_Ofc`

### Completed Work

Implemented a complete document management module that allows authenticated users to upload, view, and delete their own documents. This week establishes the document storage layer that will be used for the RAG pipeline in Week 7.

#### Backend

- Created a new **Document** SQLAlchemy model with:
  - UUID primary key
  - User ownership (`user_id`)
  - Original filename
  - Local file path
  - File type
  - File size
  - Upload status
  - Upload timestamp
  - Relationship with the `User` model

- Created an Alembic migration for the `documents` table.

- Implemented `DocumentRepository` with:
  - `create()`
  - `get_by_id()`
  - `get_by_id_and_user()`
  - `list_by_user()`
  - `delete()`

- Implemented `DocumentService` containing the business logic for:
  - File selection validation
  - File extension validation
  - File size validation (20 MB limit)
  - Automatic creation of the `uploads/` directory
  - UUID-based filename generation
  - Saving uploaded files to local storage
  - Persisting document metadata in PostgreSQL
  - Removing uploaded files if database persistence fails
  - Listing documents belonging to the authenticated user
  - Deleting both the uploaded file and its database record

- Added document API schemas:
  - `DocumentResponse`
  - `DeleteDocumentResponse`

- Created a dedicated document router with JWT-protected endpoints.

- Successfully tested all APIs using Swagger.

#### Frontend

- Created `documentService.js` with:
  - `uploadDocument()`
  - `getDocuments()`
  - `deleteDocument()`

- Created `FileUpload.jsx` featuring:
  - File picker
  - Upload button
  - Upload state
  - Success and error messages

- Created `DocumentList.jsx` featuring:
  - Document listing
  - Filename display
  - File type display
  - File size display
  - Delete action
  - Refresh support

- Updated the application sidebar by adding a collapsible **Documents** section.

- Integrated `FileUpload` and `DocumentList` into the sidebar.

- Added automatic refresh of the document list after successful uploads.

### Working Features

- Upload PDF documents
- Upload DOCX documents
- Upload TXT documents
- Store uploaded files in the local `uploads/` directory
- Store document metadata in PostgreSQL
- View uploaded documents
- Delete uploaded documents
- Delete uploaded files from local storage
- JWT-protected document management

### APIs

- `POST /api/documents/upload`
- `GET /api/documents`
- `DELETE /api/documents/{document_id}`

### Database Status

Added a new `documents` table containing:

- id
- user_id
- filename
- file_path
- file_type
- file_size
- status
- uploaded_at

### Current Status

Week 6 document management is complete. Users can upload, manage, and delete documents through both the backend APIs and the frontend interface. Uploaded files are stored locally, while their metadata is stored in PostgreSQL.

### Next Task

Begin **Week 7 — RAG Pipeline**, which will add:

- Document text extraction
- Text chunking
- Embedding generation
- Vector storage
- Semantic retrieval
- Retrieval-Augmented Generation (RAG) using uploaded documents