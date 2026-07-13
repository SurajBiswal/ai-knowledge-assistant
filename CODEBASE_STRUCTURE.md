# AI Knowledge Assistant - Codebase Structure

This document reflects the current project structure and explains the main custom code files that were added or updated in the workspace.

---

## 📁 Project Overview

```text
ai-knowledge-assistant/
├── backend/               # FastAPI backend with auth, chat, and document features
├── frontend/              # React + Vite frontend UI
├── STREAMING_IMPLEMENTATION.md
└── CODEBASE_STRUCTURE.md
```

---

## 🔧 Backend Structure

### Root backend files

- backend/requirements.txt
  - Lists the Python dependencies required for the backend.

- backend/alembic.ini
  - Alembic configuration for database migrations.

- backend/test_chunker.py
  - Tests the chunking logic for document splitting.

- backend/test_embedder.py
  - Tests embedding generation for chunks.

- backend/test_jwt.py
  - Tests JWT authentication behavior.

### backend/app/main.py
- Entry point for the FastAPI app.
- Creates the app instance, enables CORS, and includes the auth, conversation, and document routers.

### backend/app/core/

- backend/app/core/config.py
  - Loads environment variables such as API keys and JWT settings.

- backend/app/core/security.py
  - Handles password hashing, password verification, JWT creation, and token validation.

- backend/app/core/dependencies.py
  - Provides authentication dependency used by protected API routes.

### backend/app/database/

- backend/app/database/base.py
  - Shared SQLAlchemy base class for models.

- backend/app/database/session.py
  - Creates the database session and provides the FastAPI dependency for database access.

### backend/app/models/

- backend/app/models/user.py
  - Defines the users table and relationships to conversations and documents.

- backend/app/models/document.py
  - Stores uploaded document metadata such as name, path, type, size, and status.

- backend/app/models/conversation.py
  - Stores chat conversations and links them to the owning user.

- backend/app/models/message.py
  - Stores chat messages with role, content, token count, and sources.

- backend/app/models/document_chunk.py
  - Stores text chunks for RAG and includes pgvector embeddings for similarity search.

### backend/app/rag/

- backend/app/rag/chunker.py
  - Splits large text into smaller chunks with overlap for document indexing.

- backend/app/rag/embedder.py
  - Generates embeddings from text using Gemini.

### backend/app/graph/

- backend/app/graph/state.py
  - Defines the chat workflow state structure.

- backend/app/graph/graph.py
  - Builds the LangGraph workflow used for conversational processing.

- backend/app/graph/nodes.py
  - Implements the chatbot node that sends the prompt to Gemini.

### backend/app/repositories/

- backend/app/repositories/user_repository.py
  - Handles user create/read database operations.

- backend/app/repositories/conversation_repository.py
  - Handles conversation creation, lookup, rename, and listing.

- backend/app/repositories/message_repository.py
  - Handles message persistence and retrieval for conversations.

- backend/app/repositories/document_repository.py
  - Handles document metadata CRUD and listing by user.

- backend/app/repositories/document_chunk_repository.py
  - Handles creation and deletion of document chunks linked to a document.

### backend/app/services/

- backend/app/services/auth_service.py
  - Contains authentication business logic for registration and login.

- backend/app/services/chat_service.py
  - Contains chat and conversation logic, including message handling and streaming support.

- backend/app/services/document_service.py
  - Handles document upload validation, file storage, and processing workflow.

- backend/app/services/gemini_service.py
  - Wraps Gemini API calls for normal responses, streaming responses, and conversation title generation.

### backend/app/api/

- backend/app/api/auth/router.py
  - Exposes login and registration endpoints.

- backend/app/api/auth/schemas.py
  - Defines request/response validation for auth endpoints.

- backend/app/api/conversations/router.py
  - Exposes conversation creation, listing, renaming, message sending, and streaming endpoints.

- backend/app/api/conversations/schemas.py
  - Defines schemas for conversation-related requests and responses.

- backend/app/api/documents/router.py
  - Exposes upload, list, and delete endpoints for documents.

- backend/app/api/documents/schemas.py
  - Defines document-related request/response schemas.

### backend/app/schemas/

- backend/app/schemas/conversation.py
  - Shared conversation-related schema definitions.

- backend/app/schemas/message.py
  - Shared message-related schema definitions.

### backend/alembic/versions/

- Migration files are used to create and evolve the database schema for users, conversations, messages, documents, and document chunks.

---

## 🎨 Frontend Structure

### frontend/src/main.jsx
- Boots the React app into the browser.

### frontend/src/App.jsx
- Main app component that manages authentication flow and page routing.

### frontend/src/Layout.jsx
- Shared layout container for the app UI.

### frontend/src/pages/

- frontend/src/pages/LoginPage.jsx
  - Login and registration page for users.

- frontend/src/pages/ChatPage.jsx
  - Main chat page that manages conversation state and sends messages.

### frontend/src/components/

- frontend/src/components/layout/Header.jsx
  - Top app header with title and logout actions.

- frontend/src/components/layout/Sidebar.jsx
  - Sidebar for selecting conversations and starting a new chat.

- frontend/src/components/chat/ChatWindow.jsx
  - Displays the chat message list and handles scrolling behavior.

- frontend/src/components/chat/ChatInput.jsx
  - Input box used to send chat messages.

- frontend/src/components/chat/MessageBubble.jsx
  - Renders each message bubble in the chat UI.

- frontend/src/components/chat/TypingIndicator.jsx
  - Shows the loading/typing state while AI is responding.

- frontend/src/components/upload/FileUpload.jsx
  - UI for selecting and uploading documents.

- frontend/src/components/upload/DocumentList.jsx
  - Displays uploaded documents and enables deletion.

### frontend/src/services/

- frontend/src/services/api.js
  - Shared Axios instance with base URL and auth headers.

- frontend/src/services/authService.js
  - Handles frontend authentication API calls.

- frontend/src/services/conversationService.js
  - Handles conversation and chat message requests, including streaming support.

- frontend/src/services/documentService.js
  - Handles document upload, list, and delete requests.

---

## 🔄 Current Main Workflows

### Chat flow
1. User sends a message from the frontend.
2. The conversation service calls the backend message endpoint.
3. The chat service processes the request and may stream the response.
4. The UI updates the message progressively as chunks arrive.

### Document upload flow
1. User selects a file in the upload UI.
2. The frontend sends the file to the document upload endpoint.
3. The backend saves the file and stores document metadata.
4. The document is processed into chunks and embeddings for later retrieval.

### RAG flow
1. Incoming questions are matched against stored document chunks.
2. Relevant chunks are retrieved.
3. The AI uses those chunks as context for a better response.

---

## ✅ Notes on the Updated Structure

The current codebase now includes:
- document upload and management APIs
- document chunk storage with embeddings
- repository classes for document chunks
- frontend upload components and document services
- streaming chat support between frontend and backend

