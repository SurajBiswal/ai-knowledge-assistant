# AI Knowledge Assistant - Codebase Structure

This document reflects the current application structure after completion of Weeks 1–8, including authentication, conversation management, document ingestion, semantic retrieval, BM25 retrieval, hybrid search, cross-encoder reranking, grounded prompting, source citations, LangGraph orchestration, and streaming responses.

---

## 1. Project Overview

```text
ai-knowledge-assistant/
├── backend/                  # FastAPI backend application
├── frontend/                 # React + Vite frontend application
├── docs/                     # Project documentation and weekly summaries
├── CODEBASE_STRUCTURE.md     # Current repository structure overview
├── STREAMING_IMPLEMENTATION.md
├── .gitignore
├── .idea/
└── .venv/
```

---

## 2. Backend Structure

### 2.0 Compact backend tree

```text
backend/
├── app/
│   ├── api/
│   │   ├── auth/
│   │   ├── conversations/
│   │   └── documents/
│   ├── core/
│   ├── database/
│   ├── graph/
│   │   └── nodes/
│   ├── models/
│   ├── rag/
│   ├── repositories/
│   ├── schemas/
│   └── services/
├── alembic/
│   └── versions/
├── uploads/
├── alembic.ini
└── requirements.txt
```

> Note: Test files (`backend/test/`, `backend/test_*.py`) exist in the repository but are intentionally excluded from this document, which focuses on application architecture.

### 2.1 Root backend files

- `backend/requirements.txt`
  - Python dependencies for FastAPI, SQLAlchemy, Alembic, JWT, LangGraph, and Gemini integration.

- `backend/alembic.ini`
  - Alembic configuration for database migrations.

- `backend/.env`
  - Environment variables such as database URL, JWT secret, and Gemini API settings.

- `backend/uploads/`
  - Local storage directory for uploaded documents.

---

## 2.2 Application Entry Point

### `backend/app/main.py`

Initializes the FastAPI application.

Responsibilities include:

- FastAPI application creation
- Router registration
- CORS configuration
- Application startup configuration
- Health endpoint

---

## 2.3 Core Application Modules

### `backend/app/core/config.py`

Loads application configuration and environment variables.

Includes configuration for:

- Database
- JWT
- Gemini
- Application settings

### `backend/app/core/security.py`

Provides security functionality including:

- Password hashing
- Password verification
- JWT creation
- JWT validation

### `backend/app/core/dependencies.py`

Provides reusable FastAPI dependencies including:

- Database session
- Authenticated user
- Request-level dependencies

---

## 2.4 Database Layer

### `backend/app/database/base.py`

Defines the SQLAlchemy declarative base used by application models.

### `backend/app/database/session.py`

Configures SQLAlchemy database sessions and dependency injection.

---

## 2.5 Database Models

### `backend/app/models/user.py`

Represents application users and authentication-related data.

### `backend/app/models/conversation.py`

Represents conversations owned by users.

### `backend/app/models/message.py`

Stores conversation messages.

Messages can contain:

- Role
- Content
- Sources
- Timestamps
- Other message metadata

### `backend/app/models/document.py`

Stores uploaded document metadata.

### `backend/app/models/document_chunk.py`

Stores processed document chunks used by the RAG pipeline.

Chunk records contain information such as:

- Document reference
- Chunk index
- Chunk text
- Embedding
- Metadata

---

## 2.6 Repository Layer

### `backend/app/repositories/user_repository.py`

Handles user persistence and lookup operations.

### `backend/app/repositories/conversation_repository.py`

Handles conversation persistence including:

- Creation
- Lookup
- Listing
- Rename
- Delete

### `backend/app/repositories/message_repository.py`

Handles message persistence and conversation history retrieval.

### `backend/app/repositories/document_repository.py`

Handles document metadata persistence and document operations.

### `backend/app/repositories/document_chunk_repository.py`

Handles document chunk persistence and vector similarity search.

---

## 2.7 Document Ingestion and RAG Components

### `backend/app/rag/extractor.py`

Extracts text from supported document formats.

The extracted text becomes the input to the chunking stage.

### `backend/app/rag/chunker.py`

Splits extracted document text into smaller overlapping chunks.

The chunks are used as the basic retrieval units.

### `backend/app/rag/embedder.py`

Generates vector embeddings for document chunks and retrieval queries.

The project uses the configured Gemini embedding provider.

---

## 2.8 Retrieval Pipeline

The retrieval architecture evolved from semantic-only retrieval into a multi-stage retrieval pipeline.

Current architecture:

```text
                    User Question
                         │
                         ▼
                Retrieval Query
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
      Semantic Retrieval        BM25 Retrieval
             │                       │
             └───────────┬───────────┘
                         ▼
                  HybridRetriever
                         │
                         ▼
                  Candidate Chunks
                         │
                         ▼
              CrossEncoderReranker
                         │
                         ▼
                  Final Chunks
                         │
                         ▼
                   ContextBuilder
```

### `backend/app/rag/retriever.py`

Implements **semantic/vector retrieval**.

Responsibilities:

- Generate query embeddings
- Perform vector similarity search
- Return `RetrievedChunk` objects

It represents the semantic retrieval component rather than the complete retrieval pipeline.

### `backend/app/rag/bm25_retriever.py`

Implements lexical retrieval using BM25.

Responsibilities:

- Tokenize indexed chunks
- Build BM25 retrieval data
- Match lexical query terms
- Return candidate `RetrievedChunk` objects

BM25 improves retrieval for exact terms, names, identifiers, and keyword-heavy queries.

### `backend/app/rag/hybrid_retriever.py`

Combines semantic retrieval and BM25 retrieval into a single candidate set, which is then passed to the cross-encoder reranker.

Architecture:

```text
Question
   │
   ├───────────────┐
   ▼               ▼
Semantic         BM25
Retriever       Retriever
   │               │
   └───────┬───────┘
           ▼
        Merge
           ▼
    Deduplicated
     Candidates
```

The HybridRetriever improves retrieval recall by combining semantic and lexical retrieval signals.

### `backend/app/rag/cross_encoder_reranker.py`

Provides the reranking stage after hybrid retrieval.

Responsibilities:

- Receive candidate `RetrievedChunk` objects
- Score each candidate against the question
- Sort candidates according to reranking score
- Preserve the `RetrievedChunk` output structure
- Apply the requested top-K limit

It does **not** perform:

- Retrieval
- Embedding generation
- Query rewriting
- Context construction
- Prompt generation

Architecture:

```text
Question
   +
RetrievedChunk[]
        │
        ▼
 Cross Encoder
        │
        ▼
RetrievedChunk[]
```

Only the ordering of the candidate chunks is changed.

---

## 2.9 Context and Grounded Generation

### `backend/app/rag/context_builder.py`

Converts final retrieved chunks into structured context suitable for the LLM prompt.

```text
Final Retrieved Chunks
        ↓
ContextBuilder
        ↓
Structured Context
```

### `backend/app/rag/prompt_builder.py`

Constructs the grounded prompt using:

- User question
- Retrieved document context
- Grounding instructions

The resulting prompt is passed to the LLM.

### `backend/app/rag/citation_builder.py`

Builds source citation information from retrieved document chunks.

The citations are carried through the graph state and ultimately stored with assistant messages.

### `backend/app/rag/query_rewriter.py`

Transforms the original user question into a retrieval-oriented query when required.

This separates the user's conversational wording from the query used by retrieval components.

---

## 2.10 RAG Service

### `backend/app/services/rag_service.py`

Acts as the main service-level orchestration layer for document processing and retrieval.

**Document indexing responsibilities:**

```text
Document
   ↓
Extract
   ↓
Chunk
   ↓
Generate Embeddings
   ↓
Store Document Chunks
```

**Retrieval responsibilities:**

```text
Question
   ↓
Retrieve Candidates (Hybrid)
   ↓
Rerank Candidates (Cross-Encoder)
   ↓
Build Context
```

The service provides higher-level methods so the rest of the application does not need to directly coordinate the individual RAG components.

---

## 2.11 LangGraph Workflow

### `backend/app/graph/state.py`

Defines the state passed between LangGraph nodes.

The state carries information required by the conversational and RAG pipeline, including:

- User query
- Conversation information
- Messages
- Retrieved documents
- Context
- Prompt
- Sources
- Generated response

### `backend/app/graph/graph.py`

Builds the LangGraph execution workflow.

The graph connects the RAG and chatbot stages.

### `backend/app/graph/nodes/rag.py`

Implements the RAG graph node.

The RAG node coordinates:

```text
Question
   ↓
RAGService
   ↓
Retrieved Documents
   ↓
Context
   ↓
Sources
```

The node returns:

```python
{
    "retrieved_docs": ...,
    "context": ...,
    "sources": ...
}
```

Downstream graph nodes consume this state.

### `backend/app/graph/nodes/chatbot.py`

Implements the chatbot generation stage.

The chatbot node consumes the retrieved context and constructs/uses the grounded prompt before generating the answer.

Architecture:

```text
RAG Node
   │
   ├── retrieved_docs
   ├── context
   └── sources
          │
          ▼
      Chatbot Node
          │
          ▼
      Grounded Prompt
          │
          ▼
         Gemini
          │
          ▼
       Response
```

---

## 2.12 API Layer

### Authentication

- `backend/app/api/auth/router.py` — Authentication endpoints for registration and login.
- `backend/app/api/auth/schemas.py` — Pydantic request/response schemas for authentication.

### Conversations

- `backend/app/api/conversations/router.py` — Conversation and chat endpoints: creation, listing, retrieval, rename, deletion, message retrieval, chat requests, streaming chat responses.
- `backend/app/api/conversations/schemas.py` — Pydantic schemas for conversation and chat operations.

### Documents

- `backend/app/api/documents/router.py` — Document endpoints for upload, listing, and deletion.
- `backend/app/api/documents/schemas.py` — Pydantic schemas for document operations.

---

## 2.13 Services Layer

### `backend/app/services/auth_service.py`

Authentication business logic.

### `backend/app/services/chat_service.py`

Coordinates conversation-level chat operations.

Responsibilities include:

- Loading conversation history
- Saving user messages
- Executing the LangGraph workflow
- Saving assistant responses
- Streaming assistant responses
- Conversation title generation

### `backend/app/services/document_service.py`

Coordinates document upload and processing.

Responsibilities include:

```text
Upload
  ↓
Store File
  ↓
Create Document Record
  ↓
RAGService
  ↓
Extract
  ↓
Chunk
  ↓
Embed
  ↓
Persist Chunks
```

### `backend/app/services/rag_service.py`

Coordinates document indexing and the full retrieval pipeline (see section 2.10).

### `backend/app/services/gemini_service.py`

Provides the Gemini integration.

Responsibilities include:

- Standard generation
- Streaming generation
- Conversation title generation

---

## 2.14 Shared Schemas

- `backend/app/schemas/conversation.py` — Shared conversation response schemas.
- `backend/app/schemas/message.py` — Shared message response schemas.

---

## 2.15 Database Migrations

Current migrations (`backend/alembic/versions/`):

- `02c4358a66fc_create_users_conversations_messages.py` — Creates the initial users, conversations, and messages tables.
- `7062d95e0994_create_documents_table.py` — Creates the documents table.
- `1bdfce714bb4_create_document_chunks_table.py` — Creates the document chunks table used by RAG.
- `42b59302bcf3_add_hnsw_index_to_document_chunks.py` — Adds the HNSW vector index used for efficient vector similarity retrieval.
- `45bf79c8461d_add_timestamps_mode_sources.py` — Adds timestamp, mode, and source-related fields.

---

## 3. Frontend Structure

```text
frontend/
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── chat/
│   │   ├── layout/
│   │   └── upload/
│   ├── pages/
│   ├── services/
│   ├── App.jsx
│   ├── App.css
│   ├── Layout.jsx
│   ├── index.css
│   └── main.jsx
├── public/
├── index.html
├── package.json
└── vite.config.js
```

### 3.1 Frontend entry and app shell

- `frontend/package.json` — Defines frontend dependencies and scripts for Vite, React, Axios, and ESLint.
- `frontend/vite.config.js` — Vite configuration for the development server and build pipeline.
- `frontend/index.html` — Root HTML entry for the React app.
- `frontend/src/main.jsx` — Renders the React application into the browser.
- `frontend/src/App.jsx` — Main application component that manages page routing and auth-aware UI state.
- `frontend/src/Layout.jsx` — Shared shell layout used across the app.

### 3.2 Pages

- `frontend/src/pages/LoginPage.jsx` — Login and registration screen for users.
- `frontend/src/pages/ChatPage.jsx` — Main chat page: conversation selection, message rendering, sending messages, streaming assistant responses, conversation management, error handling.

### 3.3 Chat Components

- `frontend/src/components/chat/ChatWindow.jsx` — Displays the conversation message list.
- `frontend/src/components/chat/ChatInput.jsx` — Provides the user message input interface.
- `frontend/src/components/chat/MessageBubble.jsx` — Renders individual messages.
- `frontend/src/components/chat/TypingIndicator.jsx` — Provides the typing/loading UI when applicable.

### 3.4 Layout Components

- `frontend/src/components/layout/Header.jsx` — Application header with title and logout controls.
- `frontend/src/components/layout/Sidebar.jsx` — Conversation navigation and conversation management.

### 3.5 Upload Components

- `frontend/src/components/upload/FileUpload.jsx` — Document upload UI.
- `frontend/src/components/upload/DocumentList.jsx` — Displays uploaded documents and provides document management actions.

### 3.6 Frontend Services

- `frontend/src/services/api.js` — Shared Axios instance / API client and authentication headers.
- `frontend/src/services/authService.js` — Authentication API operations.
- `frontend/src/services/conversationService.js` — Conversation and chat API operations, including streaming communication with the backend.
- `frontend/src/services/documentService.js` — Document API operations.

### 3.7 Styling and static assets

- `frontend/src/App.css` — App-level styles.
- `frontend/src/index.css` — Global CSS entry point.
- `frontend/src/assets/` — Static images and shared frontend assets.
- `frontend/public/` — Static assets served by Vite.

---

## 4. Main Application Workflows

### 4.1 Authentication Flow

```text
User
 ↓
Login / Register
 ↓
Auth API
 ↓
AuthService
 ↓
JWT
 ↓
Authenticated Requests
```

### 4.2 Document Ingestion Flow

```text
User
 ↓
Upload Document
 ↓
Document API
 ↓
DocumentService
 ↓
DocumentExtractor
 ↓
DocumentChunker
 ↓
GeminiEmbedder
 ↓
DocumentChunkRepository
 ↓
PostgreSQL + pgvector
```

### 4.3 Retrieval Flow

```text
User Question
      ↓
Retrieval Query
      ↓
 ┌────┴─────┐
 ↓          ↓
Semantic    BM25
Retriever   Retriever
 ↓          ↓
 └────┬─────┘
      ↓
HybridRetriever
      ↓
Candidate Chunks
      ↓
CrossEncoderReranker
      ↓
Final Chunks
      ↓
ContextBuilder
      ↓
Grounded Context
```

### 4.4 Grounded Generation Flow

```text
User Question
      ↓
RAG Pipeline
      ↓
Retrieved + Reranked Chunks
      ↓
ContextBuilder
      ↓
Grounded Context
      ↓
PromptBuilder
      ↓
Grounded Prompt
      ↓
Gemini
      ↓
Generated Answer
```

### 4.5 LangGraph RAG Flow

```text
User Question
      ↓
LangGraph
      ↓
RAG Node
      ↓
RAGService
      ↓
HybridRetriever
      ↓
CrossEncoderReranker
      ↓
ContextBuilder
      ↓
Sources
      ↓
Chatbot Node
      ↓
Grounded Prompt
      ↓
Gemini
      ↓
Response
```

### 4.6 Streaming Chat Flow

```text
Frontend
   ↓
ChatPage
   ↓
conversationService
   ↓
Streaming Chat API
   ↓
ChatService
   ↓
LangGraph
   ↓
RAG + Grounded Prompt
   ↓
Gemini Streaming
   ↓
Response Chunks
   ↓
Frontend
   ↓
Incremental Message Rendering
```

The assistant message is progressively updated as chunks arrive from the backend.

---

## 5. Current Architecture Summary

```text
                    Frontend
                       │
                       ▼
                  FastAPI API
                       │
                       ▼
                 Service Layer
                       │
              ┌────────┴────────┐
              ▼                 ▼
         ChatService         RAGService
              │                 │
              ▼                 ▼
          LangGraph       Retrieval Pipeline
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
        SemanticRetriever                 BM25Retriever
                 │                             │
                 └──────────────┬──────────────┘
                                ▼
                         HybridRetriever
                                │
                                ▼
                     CrossEncoderReranker
                                │
                                ▼
                         ContextBuilder
                                │
                                ▼
                         PromptBuilder
                                │
                                ▼
                              Gemini
```

---

## 6. Current Capabilities

The current application includes:

- FastAPI backend
- React/Vite frontend
- JWT authentication
- User and conversation management
- Conversation history persistence
- Document upload and management
- PDF/DOCX/TXT document extraction
- Recursive document chunking
- Gemini embedding generation
- PostgreSQL + pgvector storage
- HNSW vector indexing
- Semantic retrieval
- BM25 lexical retrieval
- Hybrid retrieval
- Cross-encoder reranking
- Query rewriting
- Context construction
- Grounded prompt construction
- Source citation generation
- LangGraph-based RAG orchestration
- Gemini response generation
- Gemini streaming responses
- Frontend incremental streaming rendering

---

## 7. Architecture Evolution

The retrieval architecture evolved across the project as follows.

**Initial RAG:**

```text
Question
   ↓
Semantic Retrieval
   ↓
Context
   ↓
Gemini
```

**Hybrid Retrieval:**

```text
Question
   ↓
Semantic + BM25
   ↓
Hybrid Retrieval
   ↓
Context
   ↓
Gemini
```

**Current Retrieval Architecture (Week 8):**

```text
Question
   ↓
Semantic + BM25
   ↓
Hybrid Retrieval
   ↓
Candidate Chunks
   ↓
Cross-Encoder Reranking
   ↓
Final Chunks
   ↓
Context
   ↓
Grounded Prompt
   ↓
Gemini
   ↓
Answer
```

This layered retrieval architecture separates retrieval, reranking, context construction, prompt construction, and generation, allowing each component to evolve independently.

---

## 8. Notes on This Revision

Compared to the previous version of this document, the following changes were made:

- **`RAGService`** description updated — it now coordinates the full retrieval pipeline (hybrid retrieval + reranking + context building), not just extraction/chunking/embedding/semantic retrieval.
- **`retriever.py`** description narrowed to reflect that it implements semantic/vector retrieval specifically, not the entire retrieval system.
- **`hybrid_retriever.py`** description expanded to clarify that its candidate output feeds into the cross-encoder reranker.
- **Reranking stage** (`cross_encoder_reranker.py`) is now reflected in the RAG workflow diagrams, which previously stopped at vector similarity.
- **RAG flow (section 4)** rewritten to reflect the current multi-stage pipeline (query → hybrid retrieval → reranking → context → grounded prompt → generation), replacing the outdated single-step vector-similarity flow.
- **`backend/venv/`** removed — not present in the current backend tree (only the project-level `.venv/` exists).
- **Test files** (`backend/test/`, root-level `test_*.py`) excluded from this document by request; only application architecture is documented here.