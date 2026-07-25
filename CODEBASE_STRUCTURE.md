# AI Knowledge Assistant - Codebase Structure

This document reflects the current repository structure after the backend expansion for authentication, chat, document ingestion, retrieval-augmented generation (RAG), and streaming responses.

---

## 1. Project Overview

```text
ai-knowledge-assistant/
├── backend/                  # FastAPI backend application
├── frontend/                 # React + Vite frontend application
├── docs/                     # Project documentation and weekly summaries
├── CODEBASE_STRUCTURE.md     # Current repository structure overview
├── STREAMING_IMPLEMENTATION.md
└── README files / notes
```

---

## 2. Backend Structure

### 2.1 Root backend files

- backend/requirements.txt
  - Python dependencies for FastAPI, SQLAlchemy, Alembic, JWT, LangGraph, and Gemini integration.

- backend/alembic.ini
  - Alembic configuration for database migrations.

- backend/.env
  - Environment variables such as database URL, JWT secret, and Gemini API settings.

- backend/test_chunker.py
  - Unit tests for text chunking logic.

- backend/test_embedder.py
  - Unit tests for embedding generation.

- backend/test_jwt.py
  - Tests for JWT authentication helpers.

- backend/test_rag_node.py
  - Tests for the RAG graph node behavior.

- backend/test_retriever.py
  - Run-book retrieval script and regression check for semantic chunk retrieval.

- backend/uploads/
  - Local storage directory for uploaded documents.

- backend/venv/
  - Local Python virtual environment.

### 2.2 Application entrypoint

- backend/app/main.py
  - Initializes the FastAPI app, enables CORS, registers routers, and exposes the health endpoint.

### 2.3 Core application modules

- backend/app/core/config.py
  - Loads configuration from environment variables.

- backend/app/core/security.py
  - Handles password hashing, password verification, JWT creation, and token validation.

- backend/app/core/dependencies.py
  - Provides reusable dependencies for authentication and database access.

### 2.4 Database layer

- backend/app/database/base.py
  - Defines the SQLAlchemy base model used by all ORM entities.

- backend/app/database/session.py
  - Configures the database session and dependency injection for requests.

### 2.5 Database models

- backend/app/models/user.py
  - User model, including authentication and ownership relationships.

- backend/app/models/conversation.py
  - Conversation model linking chats to a specific user.

- backend/app/models/message.py
  - Message model for storing chat content, role, token count, and sources.

- backend/app/models/document.py
  - Document metadata model for uploaded files.

- backend/app/models/document_chunk.py
  - Chunk storage model used by the RAG system, including embedding data.

### 2.6 Repositories

- backend/app/repositories/user_repository.py
  - User create/read logic.

- backend/app/repositories/conversation_repository.py
  - Conversation creation, lookup, rename, and listing.

- backend/app/repositories/message_repository.py
  - Message persistence and retrieval.

- backend/app/repositories/document_repository.py
  - Document metadata CRUD operations and user-based listing.

- backend/app/repositories/document_chunk_repository.py
  - Chunk creation, deletion, and semantic search operations.

### 2.7 RAG and embedding pipeline

- backend/app/rag/chunker.py
  - Splits long text into smaller overlapping chunks for indexing.

- backend/app/rag/embedder.py
  - Generates embeddings for text using the configured embedding provider.

- backend/app/rag/extractor.py
  - Extracts text content from uploaded documents for processing.

- backend/app/rag/retriever.py
  - Converts user questions into embeddings and retrieves similar chunks for context grounding.

### 2.8 LangGraph-based chat workflow

- backend/app/graph/state.py
  - Defines the chat workflow state structure.

- backend/app/graph/graph.py
  - Builds the execution graph used for conversational processing.

- backend/app/graph/nodes/__init__.py
  - Package marker for graph nodes.

- backend/app/graph/nodes/chatbot.py
  - Implements the chatbot node that prepares prompts and interacts with the LLM.

- backend/app/graph/nodes/rag.py
  - Implements the retrieval-augmented generation step for grounding the response.

### 2.9 API layer

- backend/app/api/__init__.py
  - API package initializer.

- backend/app/api/auth/router.py
  - Authentication endpoints for registration and login.

- backend/app/api/auth/schemas.py
  - Pydantic schemas for auth requests and responses.

- backend/app/api/conversations/router.py
  - Conversation, message, and streaming chat endpoints.

- backend/app/api/conversations/schemas.py
  - Schemas for conversation and chat payloads.

- backend/app/api/documents/router.py
  - Document upload, listing, and deletion endpoints.

- backend/app/api/documents/schemas.py
  - Schemas for document upload and response models.

### 2.10 Services layer

- backend/app/services/auth_service.py
  - Business logic for authentication and token-supported user flows.

- backend/app/services/chat_service.py
  - Chat orchestration, conversation handling, and streaming logic.

- backend/app/services/document_service.py
  - Document upload validation, file storage, and document processing workflow; delegates document indexing to RAGService.

- backend/app/services/rag_service.py
  - Coordinates document extraction, chunking, embedding generation, chunk persistence, and semantic retrieval.

- backend/app/services/gemini_service.py
  - Wrapper around Gemini API calls for standard responses, streaming, and title generation.

### 2.11 Shared schemas

- backend/app/schemas/conversation.py
  - Shared conversation response models.

- backend/app/schemas/message.py
  - Shared message response models.

### 2.12 Database migrations

- backend/alembic/versions/02c4358a66fc_create_users_conversations_messages.py
  - Creates the initial users, conversations, and messages tables.

- backend/alembic/versions/1bdfce714bb4_create_document_chunks_table.py
  - Creates the document chunks table used by RAG.

- backend/alembic/versions/42b59302bcf3_add_hnsw_index_to_document_chunks.py
  - Adds vector index support for document chunk embeddings.

- backend/alembic/versions/45bf79c8461d_add_timestamps_mode_sources.py
  - Adds timestamp and source-related fields for messages and documents.

- backend/alembic/versions/7062d95e0994_create_documents_table.py
  - Creates the documents table for uploaded file metadata.

---

## 3. Frontend Structure

### 3.1 Frontend entry and app shell

- frontend/package.json
  - Defines frontend dependencies and scripts for Vite, React, Axios, and ESLint.

- frontend/vite.config.js
  - Vite configuration for the development server and build pipeline.

- frontend/index.html
  - Root HTML entry for the React app.

- frontend/src/main.jsx
  - Renders the React application into the browser.

- frontend/src/App.jsx
  - Main application component that manages page routing and auth-aware UI state.

- frontend/src/Layout.jsx
  - Shared shell layout used across the app.

### 3.2 Pages

- frontend/src/pages/LoginPage.jsx
  - Login and registration screen for users.

- frontend/src/pages/ChatPage.jsx
  - Main chat experience including message history and streaming chat UI.

### 3.3 Components

- frontend/src/components/layout/Header.jsx
  - Top header with app title and logout controls.

- frontend/src/components/layout/Sidebar.jsx
  - Sidebar for conversation selection and new chat creation.

- frontend/src/components/chat/ChatWindow.jsx
  - Displays the conversation messages and handles scrolling behavior.

- frontend/src/components/chat/ChatInput.jsx
  - Input area used to send new messages.

- frontend/src/components/chat/MessageBubble.jsx
  - Renders individual messages in the UI.

- frontend/src/components/chat/TypingIndicator.jsx
  - Shows loading or typing states during AI responses.

- frontend/src/components/upload/FileUpload.jsx
  - File selection UI for document uploads.

- frontend/src/components/upload/DocumentList.jsx
  - Displays uploaded documents and allows deletion.

### 3.4 Frontend services

- frontend/src/services/api.js
  - Shared Axios instance with base URL and authentication headers.

- frontend/src/services/authService.js
  - Auth-related requests for login and registration.

- frontend/src/services/conversationService.js
  - Conversation and message APIs, including streaming support.

- frontend/src/services/documentService.js
  - Upload, listing, and deletion APIs for documents.

### 3.5 Styling and static assets

- frontend/src/App.css
  - App-level styles.

- frontend/src/index.css
  - Global CSS entry point.

- frontend/public/
  - Static assets served by Vite.

---

## 4. Main Application Workflows

### 4.1 Authentication flow
1. User enters login or registration details in the frontend.
2. The frontend calls the auth API in the backend.
3. The backend validates credentials and issues JWT-based access.
4. Protected routes then use the token for secure requests.

### 4.2 Chat flow
1. The user sends a chat message from the frontend.
2. The conversation API forwards the request to the backend chat service.
3. The backend may use the graph workflow and RAG retrieval to produce a grounded response.
4. Streaming chunks are sent back to the UI progressively.

### 4.3 Document upload and indexing flow
1. A user uploads a document through the frontend upload UI.
2. The backend stores the file locally and records metadata in the database.
3. The document text is extracted and split into chunks.
4. Embeddings are generated and stored for semantic retrieval later.

### 4.4 RAG flow
1. A user asks a question.
2. The backend retrieves relevant document chunks using vector similarity.
3. Those chunks are passed into the LLM context.
4. The response is generated with document-grounded information.

---

## 5. What the Current Codebase Includes

The repository now contains:
- a full FastAPI backend with authentication and protected routes
- conversation and message persistence
- document upload and metadata management
- chunking and embedding-based retrieval for RAG
- LangGraph-based orchestration for conversational workflows
- a React/Vite frontend with login, chat, and document upload features
- streaming support between the frontend and backend

This structure is intended to serve as a reliable map for navigating the project and understanding how the backend and frontend pieces interact.

