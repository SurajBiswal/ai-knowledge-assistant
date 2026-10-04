# KnowledgeAI — AI Knowledge Assistant

> An end-to-end, production-grade conversational AI and Agentic RAG platform featuring multi-stage hybrid retrieval, cross-encoder reranking, LangGraph tool calling, streaming responses, and encrypted multi-LLM provider orchestration.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Key Capabilities](#key-capabilities)
3. [System Architecture](#system-architecture)
4. [RAG Pipeline Architecture](#rag-pipeline-architecture)
5. [Agentic Tool Calling & LangGraph Workflow](#agentic-tool-calling--langgraph-workflow)
6. [Dynamic Multi-LLM Provider System](#dynamic-multi-llm-provider-system)
7. [Repository Structure](#repository-structure)
8. [Database Schema & Models](#database-schema--models)
9. [API Reference](#api-reference)
10. [Technology Stack](#technology-stack)
11. [Local Development Setup](#local-development-setup)
12. [Project Evolution (Weeks 1–9+)](#project-evolution-weeks-19)
13. [Future Roadmap](#future-roadmap)
14. [Contributing & Continuing This File](#contributing--continuing-this-file)

---

## Project Overview

**KnowledgeAI** is an AI Engineering platform designed to unify three foundational generative AI paradigms:

- **Conversational AI (ChatGPT-style):** Stateful, multi-turn dialogues with session history and real-time streaming output.
- **Document Understanding & Grounding (NotebookLM-style):** Multi-format document ingestion (PDF, DOCX, TXT), semantic chunking, high-dimensional vector search with HNSW indexing, and precise citations with page numbers and source excerpts.
- **Agentic Tool Execution (Perplexity-style):** Autonomous reasoning via LangGraph state machines, deciding whether to answer directly, perform user-scoped document retrieval, query database workspace metrics, or search the live web via Tavily.

The application is engineered with an emphasis on **production design patterns**: layered service-repository architecture, strict tenant isolation, symmetric Fernet encryption for user credentials, and provider-neutral model abstractions supporting both proprietary and open-source models.

---

## Key Capabilities

- **User Authentication & Tenant Isolation**: Secure registration and login using JWT access tokens and bcrypt password hashing. All conversations, uploaded documents, vector chunks, and provider credentials are strictly isolated per user.
- **Multi-Format Document Ingestion**: Ingests `.pdf`, `.docx`, and `.txt` files up to 20MB. Automatically extracts text, partitions into overlapping recursive chunks, generates 768-dimensional embeddings, and indexes them in PostgreSQL using pgvector.
- **Advanced Multi-Stage Retrieval**:
  - **Query Rewriter**: Translates conversational questions into keyword-optimized search queries.
  - **Hybrid Search**: Fuses semantic vector retrieval (cosine distance) with lexical retrieval (BM25 keyword matching).
  - **Cross-Encoder Reranking**: Re-scores candidate passages using `cross-encoder/ms-marco-MiniLM-L-6-v2` for high retrieval precision.
  - **Source Citations**: Produces catalog-style citations referencing document titles, page numbers, and excerpts.
- **LangGraph Agentic Tool Calling**:
  - Uses a cyclical `StateGraph` (`agent -> conditional router -> tool node -> agent -> END`).
  - Supports three tools: `search_documents`, `get_workspace_stats`, and `web_search`.
- **Dynamic Multi-LLM Provider Support**:
  - Provider-neutral contract (`ToolCallingLLM`) allowing dynamic switching between Google Gemini and OpenAI-compatible endpoints (OpenAI, Ollama, Groq, vLLM, LM Studio).
  - Encrypted credential storage (Fernet symmetric key encryption) with runtime request-scoped decryption.
  - Live provider connection testing and activation via the UI Settings modal.
- **Real-Time Streaming**: HTTP chunked streaming (`StreamingResponse`) with frontend incremental rendering via native `ReadableStream`, providing instant response feedback while persisting full message history and citations upon completion.
- **Modern Responsive Frontend**: React 19 + Vite 8 styled with Tailwind CSS 4, supporting light/dark theme toggle, drag-and-drop file upload, custom markdown rendering with syntax-highlighted code blocks and copy buttons.

---

## System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        React 19 Frontend (Vite)                        │
│  Chat UI · Markdown Renderer · Document Manager · Provider Settings   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / Streaming (Fetch)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application Gateway                     │
│    /api/auth     /api/conversations     /api/documents     /api/ai    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                              Service Layer                             │
│  AuthService · ChatService · DocumentService · RAGService · LLMService │
└──────────────────┬────────────────────────────────┬────────────────────┘
                   │                                │
                   ▼                                ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│       LangGraph Agent Workflow       │  │    Multi-Stage RAG Pipeline   │
│   Agent Node ⇆ Tool Node Loop        │  │  Extract → Chunk → Embed     │
│   Routing: should_use_tool()         │  │  Hybrid Search (Vector+BM25) │
│   Tools: RAG, DB Stats, Tavily Web   │  │  Cross-Encoder Reranker      │
└──────────────────┬───────────────────┘  └──────────────┬───────────────┘
                   │                                     │
                   ▼                                     ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│      Dynamic LLM Provider Factory    │  │   PostgreSQL 16 + pgvector   │
│  Gemini SDK · OpenAI Compatible SDK  │  │   HNSW Cosine Vector Index   │
│  Fernet Credential Decryption        │  │   Users, Chats, Docs, Keys   │
└──────────────────────────────────────┘  └──────────────────────────────┘
```

---

## RAG Pipeline Architecture

The retrieval system employs a multi-stage approach to balance high recall with maximum relevance precision:

```text
                             User Question
                                   │
                                   ▼
                             QueryRewriter
                     (Optimizes search keywords)
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
           SemanticRetriever                BM25Retriever
       (PostgreSQL pgvector HNSW)       (Lexical Token Match)
                    │                             │
                    └──────────────┬──────────────┘
                                   ▼
                            HybridRetriever
                     (Merge & Deduplicate Chunks)
                                   │
                                   ▼
                         CrossEncoderReranker
                 (ms-marco-MiniLM-L-6-v2 Pair Scoring)
                                   │
                                   ▼
                         Top-K Filtered Chunks
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
             ContextBuilder                CitationBuilder
        (Constructs Prompt Context)   (Builds Source References)
                    │                             │
                    ▼                             ▼
              Grounded Prompt             Source Metadata
                    │                             │
                    ▼                             ▼
               LLM Response            Assistant Message with
              Generation Turn           Library Card Citations
```

### Ingestion Details
1. **Extraction**: `DocumentExtractor` reads text from PDF (`pypdf`), DOCX (`docx`), or plain text files.
2. **Chunking**: `DocumentChunker` uses `RecursiveCharacterTextSplitter` with `chunk_size = 1000` and `chunk_overlap = 200`, calculating exact character boundaries.
3. **Embedding**: `GeminiEmbedder` calls Google's `gemini-embedding-001` configured for 768-dimensional vectors.
4. **Storage**: Vector records are saved to `document_chunks` with an HNSW index (`m=16`, `ef_construction=64`, `vector_cosine_ops`).

---

## Agentic Tool Calling & LangGraph Workflow

The chat engine uses a cyclical LangGraph state machine where the active LLM inspects available tools and decides whether to invoke an action or provide an immediate answer:

```text
                  START
                    │
                    ▼
              [ Agent Node ]
      (User-selected LLM evaluates)
                    │
                    ▼
             should_use_tool?
               /          \
      [Yes, call needed]   [No, answer ready]
             │                     │
             ▼                     ▼
       [ Tool Node ]              END
   (Executes from Registry)        │
             │                     ▼
             ▼              Stream/Persist
       [ Agent Node ]       Assistant Reply
   (Consumes tool result)
             │
             ▼
        More tools?
        ├── Yes ──► [ Tool Node ]
        └── No  ──► END
```

### Available Tools

| Tool Name | Description | Invocation Triggers |
| :--- | :--- | :--- |
| `search_documents` | Scoped search over user uploaded documents using the full Hybrid + Reranker RAG pipeline | User questions referencing uploaded files, specific policies, uploaded notes, or domain knowledge |
| `get_workspace_stats` | Parameterized count queries returning the user's total documents, chunks, conversations, and messages | Queries like *"How many documents have I uploaded?"* or *"What is in my workspace?"* |
| `web_search` | Real-time public web search using Tavily API | Questions requiring current events, external documentation, or real-time web facts |

---

## Dynamic Multi-LLM Provider System

Rather than hardcoding a single AI provider, KnowledgeAI incorporates a provider-neutral orchestration architecture:

1. **Provider-Neutral Contract (`app/llm/base.py`)**:
   Defines common dataclasses (`ToolDefinition`, `ToolCall`, `ToolResult`, `ModelResponse`, `ToolCallingConversation`) and the abstract interface `ToolCallingLLM`.
2. **Pluggable Adapters**:
   - `GeminiToolCallingLLM`: Interacts with Google Gemini models.
   - `OpenAICompatibleToolCallingLLM`: Interacts with OpenAI, Groq, Ollama, LocalAI, vLLM, or any standard `/v1/chat/completions` endpoint.
3. **Encrypted Security Layer (`CredentialEncryptionService`)**:
   User API keys are encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256). The plaintext key is decrypted in memory only for the duration of an active user turn.
4. **Runtime Resolution (`LLMProviderFactory`)**:
   Before initiating a chat turn, the factory verifies that the user has an active, successfully verified provider profile. Streaming endpoints validate this check *before* writing headers to return clear error responses.
5. **Interactive UI Management**:
   The frontend includes a dedicated Settings panel for creating profiles, setting custom models, adjusting timeout thresholds, running live connection tests, and toggling active status.

---

## Repository Structure

```text
ai-knowledge-assistant/
├── backend/
│   ├── alembic/                      # Database migrations
│   │   ├── versions/                 # Versioned schema migration scripts
│   │   └── env.py                    # Alembic migration environment
│   ├── app/
│   │   ├── api/                      # FastAPI routers & endpoint schemas
│   │   │   ├── auth/                 # User registration, login, profile (/api/auth)
│   │   │   ├── conversations/        # Chat sessions, messages, streaming (/api/conversations)
│   │   │   ├── documents/            # Document upload, listing, deletion (/api/documents)
│   │   │   └── llm_providers/        # Provider profiles, testing, activation (/api/ai)
│   │   ├── core/                     # Configuration, security, dependencies
│   │   │   ├── config.py             # Environment settings
│   │   │   ├── dependencies.py       # Auth & database session injection
│   │   │   └── security.py           # Password hashing & JWT issuance
│   │   ├── database/                 # SQLAlchemy session & base model
│   │   ├── graph/                    # LangGraph orchestration engine
│   │   │   ├── nodes/                # Agent, tool, and RAG execution nodes
│   │   │   ├── graph.py              # StateGraph definition & compilation
│   │   │   ├── routing.py            # Conditional routing decisions
│   │   │   └── state.py              # ChatState typing definition
│   │   ├── llm/                      # Provider-neutral model layer
│   │   │   ├── base.py               # ToolCallingLLM interface & data types
│   │   │   ├── factory.py            # Runtime request-scoped client factory
│   │   │   ├── gemini.py             # Google Gemini implementation
│   │   │   └── openai_compatible.py  # OpenAI-compatible API implementation
│   │   ├── models/                   # SQLAlchemy declarative models
│   │   ├── rag/                      # Advanced RAG subsystem
│   │   │   ├── bm25_retriever.py     # BM25 lexical retriever
│   │   │   ├── chunker.py            # Recursive character chunking
│   │   │   ├── citation_builder.py   # Citation formatting and deduplication
│   │   │   ├── context_builder.py    # Structured context formatting
│   │   │   ├── cross_encoder_reranker.py # Cross-encoder neural reranker
│   │   │   ├── embedder.py           # Vector embedding generator
│   │   │   ├── extractor.py          # Document text extraction (PDF/DOCX/TXT)
│   │   │   ├── hybrid_retriever.py   # Semantic + BM25 fusion
│   │   │   ├── prompt_builder.py     # Grounded system prompt generator
│   │   │   ├── query_rewriter.py     # Query refinement
│   │   │   └── retriever.py          # Vector similarity retrieval
│   │   ├── repositories/             # Data access repository layer
│   │   ├── schemas/                  # Shared Pydantic response models
│   │   ├── services/                 # Business logic orchestration layer
│   │   ├── tools/                    # Tool registry & tool implementations
│   │   │   ├── base.py               # BaseTool abstract generic class
│   │   │   ├── document_search.py    # RAG document search tool
│   │   │   ├── registry.py           # Tool registry collection
│   │   │   ├── tool_registry_factory.py # User-scoped tool registry builder
│   │   │   ├── web_search.py         # Tavily web search tool
│   │   │   └── workspace_stats.py    # Database metrics tool
│   │   └── main.py                   # FastAPI initialization & CORS
│   ├── test/                         # Unit, integration, & end-to-end tests
│   ├── uploads/                      # Local document storage
│   ├── alembic.ini                   # Alembic database configuration
│   └── requirements.txt              # Backend Python dependencies
├── frontend/
│   ├── public/                       # Static public assets
│   ├── src/
│   │   ├── assets/                   # Images and branding icons
│   │   ├── components/
│   │   │   ├── chat/                 # ChatWindow, ChatInput, MessageBubble, TypingIndicator
│   │   │   ├── layout/               # Header, Sidebar, Mark, ThemeToggle
│   │   │   ├── settings/             # LanguageModelSettings modal
│   │   │   └── upload/               # FileUpload, DocumentList
│   │   ├── pages/                    # LoginPage, ChatPage
│   │   ├── services/                 # API clients (auth, conversation, doc, provider)
│   │   ├── App.jsx                   # Root application state & client routing
│   │   ├── index.css                 # Global styles & Tailwind entry
│   │   └── main.jsx                  # React DOM mount point
│   ├── package.json                  # Frontend dependencies & scripts
│   └── vite.config.js                # Vite build and server config
├── docs/                             # Engineering documentation & weekly summaries
│   └── weeks/                        # Detailed weekly progress reports (Weeks 1–9)
├── CODEBASE_STRUCTURE.md             # Codebase component overview
├── STREAMING_IMPLEMENTATION.md       # Streaming mechanics guide
└── README.md                         # Main repository documentation
```

---

## Database Schema & Models

KnowledgeAI runs on PostgreSQL with the `pgvector` extension. The schema is tracked with Alembic migrations:

```text
 ┌──────────────────────────┐             ┌──────────────────────────┐
 │          users           │ 1         * │      conversations       │
 ├──────────────────────────┤────────────►├──────────────────────────┤
 │ id (UUID, PK)            │             │ id (UUID, PK)            │
 │ email (VARCHAR, UNIQUE)  │             │ user_id (UUID, FK)       │
 │ password_hash (VARCHAR)  │             │ title (VARCHAR)          │
 │ name (VARCHAR)           │             │ mode (VARCHAR)           │
 │ created_at, updated_at   │             │ created_at, updated_at   │
 └─────────────┬────────────┘             └────────────┬─────────────┘
               │ 1                                     │ 1
               │                                       │
               │ *                                     │ *
 ┌─────────────▼────────────┐             ┌────────────▼─────────────┐
 │        documents         │ 1         * │         messages         │
 ├──────────────────────────┤────────────►├──────────────────────────┤
 │ id (UUID, PK)            │             │ id (UUID, PK)            │
 │ user_id (UUID, FK)       │             │ conversation_id (UUID)   │
 │ filename (VARCHAR)       │             │ role (user/assistant)    │
 │ file_path (VARCHAR)      │             │ content (TEXT)           │
 │ file_type (VARCHAR)      │             │ sources (JSONB)          │
 │ file_size (INT)          │             │ created_at               │
 │ status (VARCHAR)         │             └──────────────────────────┘
 └─────────────┬────────────┘
               │ 1
               │
               │ *
 ┌─────────────▼────────────────────────────────────────┐
 │                   document_chunks                    │
 ├──────────────────────────────────────────────────────┤
 │ id (UUID, PK)                                        │
 │ document_id (UUID, FK, CASCADE)                      │
 │ chunk_text (TEXT)                                    │
 │ chunk_index (INT)                                    │
 │ embedding (VECTOR(768))   [HNSW Cosine Index]        │
 │ metadata (JSONB: char_start, char_end, etc.)         │
 └──────────────────────────────────────────────────────┘

 ┌──────────────────────────┐             ┌──────────────────────────┐
 │      llm_providers       │ 1         * │   llm_provider_profiles  │
 ├──────────────────────────┤────────────►├──────────────────────────┤
 │ id (UUID, PK)            │             │ id (UUID, PK)            │
 │ code (VARCHAR, UNIQUE)   │             │ user_id (UUID, FK)       │
 │ name (VARCHAR)           │             │ provider_id (UUID, FK)   │
 │ protocol (VARCHAR)       │             │ profile_name (VARCHAR)   │
 │ is_enabled (BOOLEAN)     │             │ base_url (VARCHAR)       │
 └──────────────────────────┘             │ model (VARCHAR)          │
                                          │ encrypted_api_key (TEXT) │
                                          │ timeout_seconds (INT)    │
                                          │ is_active (BOOLEAN)      │
                                          │ last_test_status (STR)   │
                                          └──────────────────────────┘
```

---

## API Reference

### Authentication (`/api/auth`)
- `POST /api/auth/register` — Create a new user account (`name`, `email`, `password`).
- `POST /api/auth/login` — Authenticate and receive a JWT Bearer access token.
- `GET /api/auth/me` — Retrieve profile data for the authenticated user.

### Conversations & Messages (`/api/conversations`)
- `GET /api/conversations` — List all conversations for the user.
- `POST /api/conversations` — Create a new conversation (`title`, `mode`).
- `PATCH /api/conversations/{id}` — Rename a conversation title.
- `DELETE /api/conversations/{id}` — Delete a conversation and message history.
- `GET /api/conversations/{id}/messages` — Fetch message history with source citations.
- `POST /api/conversations/{id}/messages` — Send a message (synchronous execution).
- `POST /api/conversations/{id}/messages/stream` — Send a message with real-time plain text chunk streaming.

### Documents (`/api/documents`)
- `POST /api/documents/upload` — Upload a document (`multipart/form-data`: PDF, DOCX, TXT) and trigger ingestion.
- `GET /api/documents` — List uploaded documents for the authenticated user.
- `DELETE /api/documents/{id}` — Remove a document and cascade-delete indexed vector chunks.

### AI Provider Profiles (`/api/ai`)
- `GET /api/ai/providers` — List available provider types (Gemini, OpenAI-compatible).
- `GET /api/ai/provider-profiles` — List configured profiles for the user.
- `POST /api/ai/provider-profiles` — Register a new provider configuration (stores encrypted API key).
- `PUT /api/ai/provider-profiles/{id}` — Update an existing profile.
- `DELETE /api/ai/provider-profiles/{id}` — Remove a provider profile.
- `POST /api/ai/provider-profiles/{id}/test` — Perform a live connection test against the model endpoint.
- `POST /api/ai/provider-profiles/{id}/activate` — Set a profile as active for subsequent chat queries.

### System
- `GET /health` — Healthcheck endpoint returning API availability status.

---

## Technology Stack

### Backend
- **Core Framework**: FastAPI, Uvicorn, Starlette
- **State Machine & Agent Flow**: LangGraph, LangChain Core
- **Database & ORM**: PostgreSQL 16, pgvector, SQLAlchemy 2.0, Alembic
- **Security & Encryption**: Cryptography (Fernet symmetric encryption), Passlib, Bcrypt, Python-Jose (JWT)
- **Document Processing**: PyPDF, Python-docx, LangChain Text Splitters
- **Search & Embeddings**: Google GenAI SDK (`gemini-embedding-001`), Rank-BM25, Sentence-Transformers (`ms-marco-MiniLM-L-6-v2`)
- **Web Intelligence**: Tavily Python SDK

### Frontend
- **Framework & Build**: React 19, Vite 8
- **Styling**: Tailwind CSS 4
- **HTTP & Streaming**: Axios, Fetch API (`ReadableStream`)
- **Typography & Icons**: Custom SVG iconography, mono/serif theme aesthetic

---

## Local Development Setup

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** & npm
- **PostgreSQL 15+** with the **`pgvector`** extension installed

### 2. Database Preparation
Ensure your PostgreSQL instance is running and create the database with pgvector:

```sql
CREATE DATABASE ai_knowledge_assistant;
\c ai_knowledge_assistant
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `backend/.env` file with the following variables:

```ini
# Database Connection (with pgvector enabled)
DATABASE_URL=postgresql://<user>:<password>@localhost:5432/ai_knowledge_assistant

# AI & Tool API Keys
GEMINI_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Security & Encryption Keys
# Generate a Fernet key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CREDENTIAL_ENCRYPTION_KEY=your_base64_fernet_key_here

# JWT Authentication
JWT_SECRET_KEY=your_secure_jwt_secret_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Run database migrations:

```bash
alembic upgrade head
```

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` (interactive documentation at `http://localhost:8000/docs`).

### 4. Frontend Setup

```bash
# In a new terminal window, navigate to the frontend directory
cd frontend

# Install npm packages
npm install
```

Ensure `frontend/.env` points to the backend:

```ini
VITE_API_BASE_URL=http://localhost:8000
```

Start the Vite development server:

```bash
npm run dev
```

Open your browser at `http://localhost:5173`.

---

## Project Evolution (Weeks 1–9+)

- **Week 1 — Foundation & Initial Pipeline**: FastAPI initial configuration, basic Gemini chat endpoints, LangGraph simple graph integration, React client interface.
- **Week 2 — Database Persistence**: PostgreSQL integration with SQLAlchemy, Alembic migration workflow, user conversation and message history persistence.
- **Week 3 — Real-Time Streaming**: Implemented chunked HTTP `StreamingResponse`, native `ReadableStream` frontend consumer, and real-time incremental rendering.
- **Week 4 — Authentication & Multi-Tenancy**: Added password hashing with bcrypt, JWT token generation and verification, user-isolated conversations.
- **Week 5 & 6 — Document Management**: Document upload pipeline supporting PDF, DOCX, and TXT files with format validation and size restrictions.
- **Week 7 — RAG Foundation**: Enabled PostgreSQL `pgvector`, recursive character text chunking, Gemini vector embeddings (768d), HNSW vector index creation, and initial semantic retrieval.
- **Week 8 — Advanced Multi-Stage RAG**:
  - Implemented Query Rewriting for search query transformation.
  - Implemented BM25 lexical retriever alongside semantic retriever.
  - Built Hybrid Retriever merging and deduplicating lexical and vector results.
  - Added Cross-Encoder reranking (`ms-marco-MiniLM-L-6-v2`) to re-rank candidate chunks.
  - Built Grounded Prompt Builder and Citation Builder formatting page numbers and excerpts.
- **Week 9 — Agentic Tool Calling & LangGraph Integration**:
  - Built generic `BaseTool` system with strict Pydantic schemas.
  - Implemented tools: `search_documents`, `get_workspace_stats`, and `web_search` (Tavily).
  - Built `ToolRegistry` and `ToolRegistryFactory` ensuring user tenancy isolation.
  - Re-architected LangGraph state machine with conditional routing (`should_use_tool`).
- **Post-Week 9 — Dynamic Multi-LLM Provider Architecture**:
  - Built provider-neutral model contract (`ToolCallingLLM`).
  - Implemented Gemini and OpenAI-compatible client adapters.
  - Implemented symmetric Fernet encryption for user credentials (`CredentialEncryptionService`).
  - Created runtime request-scoped `LLMProviderFactory`.
  - Added settings management endpoints and responsive frontend configuration modal with live connection verification.

---

## Future Roadmap

The system is designed to evolve into a full-scale enterprise AI ecosystem:

- [ ] **Model Context Protocol (MCP)**: Native integration with MCP servers to standardize tool consumption across external services and workflows.
- [ ] **Router & Intent Classifier Agent**: Intelligent semantic routing to classify incoming queries before graph execution (e.g., coding, research, direct chat, summarization).
- [ ] **Multi-Agent Collaboration**: Specialized worker agents (Researcher, Critic, Synthesizer) orchestrated via LangGraph supervisor patterns.
- [ ] **Long-Term User Memory**: Semantic memory store across conversation sessions to remember user preferences, context, and project guidelines.
- [ ] **Evaluation Framework**: Automated RAG evaluation (RAGAS / TruLens) measuring faithfulness, answer relevancy, and context recall.
- [ ] **High-Performance Caching & Rate Limiting**: Redis integration for semantic caching of vector queries and rate-limiting API endpoints.
- [ ] **Containerization & CI/CD**: Production Dockerfile, `docker-compose.yml` for local multi-container development, and GitHub Actions CI pipelines.
- [ ] **Cloud Deployment**: Production deployment on AWS (ECS / Fargate, RDS PostgreSQL with pgvector, S3 for document storage).

---

## Contributing & Continuing This File

This `README.md` is intended as a living architectural document for the project. When implementing new features:

1. Update the **Key Capabilities** section when user-facing features change.
2. Maintain the **System Architecture** and **RAG Pipeline** diagrams when adding nodes, routers, or storage layers.
3. Keep the **Database Schema & Models** in sync with new Alembic migrations.
4. Document any new tools added to the `ToolRegistry` in the **Available Tools** table.
5. Record completed milestones under the **Project Evolution** section and check off items in the **Future Roadmap**.

