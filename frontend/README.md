# AI Knowledge Assistant

A production-oriented **AI Knowledge Assistant Platform** built incrementally as an AI Engineering portfolio project.

The project combines conversational AI, document-based RAG, hybrid retrieval, cross-encoder reranking, grounded generation, source citations, streaming responses, and tool calling. The architecture is designed to evolve toward multi-agent orchestration, long-term memory, evaluation, caching, Docker, CI/CD, and AWS deployment.

> **Current status:** Weeks 1–8 are complete. Week 9 — Tool Calling is in progress. Parts 1–4 of Week 9 are complete, and the next milestone is the Tool Registry.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Why This Project](#why-this-project)
- [Current Status](#current-status)
- [Architecture](#architecture)
- [End-to-End Request Flow](#end-to-end-request-flow)
- [RAG Architecture](#rag-architecture)
- [Tool Calling Architecture](#tool-calling-architecture)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Implemented Features](#implemented-features)
- [API Endpoints](#api-endpoints)
- [Database](#database)
- [Local Setup](#local-setup)
- [Running the Application](#running-the-application)
- [Development Workflow](#development-workflow)
- [Week-by-Week Evolution](#week-by-week-evolution)
- [Future Roadmap](#future-roadmap)
- [Architecture Principles](#architecture-principles)
- [Interview-Level Explanation](#interview-level-explanation)

---

# Project Overview

The AI Knowledge Assistant is designed as a combination of:

- ChatGPT-style conversational interaction
- NotebookLM-style document understanding
- Perplexity-style web/tool-assisted answers
- Persistent conversation history
- Document-grounded answers with citations
- Tool calling for application capabilities
- Future long-term memory and multi-agent collaboration

The system is being built incrementally rather than as a single large implementation.

The core architectural progression is:

```text
Simple Chat
    ↓
Persistent Conversations
    ↓
Authentication
    ↓
Document Upload
    ↓
RAG Foundation
    ↓
Advanced RAG
    ↓
Tool Calling
    ↓
MCP
    ↓
Router Agent
    ↓
Multi-Agent System
    ↓
Long-Term Memory
    ↓
Evaluation
    ↓
Caching / Rate Limiting
    ↓
Docker / CI/CD
    ↓
AWS Deployment
```

---

# Why This Project

The project is intentionally designed to demonstrate practical AI Engineering concepts rather than only calling an LLM API.

It demonstrates:

- FastAPI backend architecture
- React frontend development
- JWT authentication
- PostgreSQL and SQLAlchemy
- Repository pattern
- LangGraph state-machine orchestration
- Document ingestion
- Embeddings
- pgvector
- HNSW vector indexing
- Semantic retrieval
- BM25 lexical retrieval
- Hybrid retrieval
- Cross-encoder reranking
- Query rewriting
- Context engineering
- Grounded prompt generation
- Source citations
- Streaming LLM responses
- Tool calling
- Conditional graph routing
- Future MCP integration
- Future multi-agent orchestration
- Future RAGAS evaluation
- Future Redis caching/rate limiting
- Future Docker and AWS deployment

The project design intentionally favors understandable, modular components so each architectural decision can be explained in an interview.

---

# Current Status

## Completed

### Weeks 1–6

- Project foundation
- React frontend
- FastAPI backend
- Basic Gemini chat
- LangGraph integration
- Conversation persistence
- Streaming responses
- JWT authentication
- Document upload and management
- PDF/DOCX/TXT extraction

### Week 7 — RAG Foundation

Completed:

- PostgreSQL pgvector
- `document_chunks` table
- 768-dimensional embeddings
- HNSW vector index
- Recursive document chunking
- Gemini embeddings
- Document extraction
- Semantic retrieval
- LangGraph RAG node
- RAG service orchestration
- Repository-based data access

### Week 8 — Advanced RAG

Completed:

- Part 1 — Query Rewriting
- Part 2 — Context Builder
- Part 3 — Grounded Prompt Generation
- Part 4 — Source Citations
- Part 5 — Hybrid Search
- Part 6 — Cross-Encoder Reranking
- Part 7 — Retrieval Pipeline Refactor

Current RAG pipeline:

```text
User Question
      ↓
Query Rewriter
      ↓
Hybrid Retriever
   ┌──┴───────────────┐
   ↓                  ↓
Semantic             BM25
Retriever            Retriever
   ↓                  ↓
   └─────── Merge ────┘
              ↓
        Deduplicate
              ↓
      Candidate Chunks
              ↓
    Cross-Encoder Reranker
              ↓
       Final Chunks
              ↓
        ContextBuilder
              ↓
        PromptBuilder
              ↓
       Grounded Prompt
              ↓
            Gemini
              ↓
        Grounded Answer
              ↓
       Source Citations
```

### Week 9 — Tool Calling

Current progress:

- Part 1 — Tool Architecture: complete
- Part 2 — `search_documents`: complete
- Part 3 — `get_workspace_stats`: complete
- Part 4 — `web_search`: complete
- Part 5 — Tool Registry: next
- Part 6 — LLM Tool Calling: upcoming
- Part 7 — LangGraph Tool Node: upcoming
- Part 8 — End-to-End Tool Loop and Validation: upcoming

The central Week 9 objective is:

```text
User
 ↓
LLM / Agent
 ↓
Structured Tool Call
 ↓
Conditional LangGraph Routing
 ↓
Tool Execution
 ↓
Tool Result
 ↓
LLM
 ↓
Final Answer
```

MCP is intentionally **not part of the current Week 9 implementation**. It is planned as Week 9.5.

---

# Architecture

The project is organized into five conceptual layers.

```text
┌────────────────────────────────────────────────────┐
│                  React Frontend                    │
│              React + Vite + JavaScript             │
└───────────────────────┬────────────────────────────┘
                        │ HTTP / SSE
                        ▼
┌────────────────────────────────────────────────────┐
│                  FastAPI Backend                   │
│       Auth · Chat · Documents · APIs               │
└───────────────────────┬────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│                Application Services                │
│ AuthService · ChatService · DocumentService        │
│ RAGService · GeminiService                         │
└───────────────────────┬────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│                 LangGraph Engine                  │
│       State · RAG · LLM · Tool Calling             │
└───────────────┬──────────────────┬─────────────────┘
                │                  │
                ▼                  ▼
       ┌────────────────┐   ┌──────────────────┐
       │ RAG Pipeline   │   │ Tool Pipeline    │
       │                │   │                  │
       │ Hybrid Search  │   │ Document Search  │
       │ Reranker       │   │ Workspace Stats  │
       │ Context        │   │ Web Search       │
       └───────┬────────┘   └────────┬─────────┘
               │                     │
               └──────────┬──────────┘
                          ▼
              ┌──────────────────────┐
              │ PostgreSQL + pgvector│
              │ External Search APIs │
              └──────────────────────┘
```

The future architecture will add:

```text
Redis
MCP
Router
Memory
Multi-Agent System
RAGAS
LangSmith
Docker
AWS
CI/CD
```

---

# End-to-End Request Flow

For a normal chat request:

```text
React UI
   ↓
POST /api/conversations/{id}/messages
   ↓
JWT Authentication
   ↓
ChatService
   ↓
LangGraph
   ↓
RAG / LLM processing
   ↓
Gemini
   ↓
Response
   ↓
PostgreSQL
```

For streaming:

```text
React
   ↓
Streaming Chat API
   ↓
ChatService
   ↓
LangGraph
   ↓
Grounded Prompt
   ↓
Gemini Streaming
   ↓
Response Chunks
   ↓
SSE
   ↓
React incremental rendering
```

---

# RAG Architecture

The RAG system evolved from semantic-only retrieval into a multi-stage retrieval architecture.

## Document Ingestion

```text
Uploaded PDF / DOCX / TXT
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

## Retrieval

```text
User Question
      ↓
Query Rewriter
      ↓
Rewritten Query
      ↓
 ┌────┴──────────────┐
 ↓                   ↓
Semantic             BM25
Search               Search
 ↓                   ↓
 └──────── Merge ────┘
          ↓
     Deduplicate
          ↓
 Candidate Pool
          ↓
Cross-Encoder Reranker
          ↓
 Final Ranked Chunks
          ↓
 ContextBuilder
          ↓
 PromptBuilder
          ↓
 Grounded Prompt
          ↓
 Gemini
          ↓
 Answer + Sources
```

## Why two retrieval stages?

The project deliberately separates:

```text
Candidate Retrieval
    ↓
Semantic + BM25
```

from:

```text
Precision Ranking
    ↓
Cross-Encoder
```

Semantic search provides meaning-based matching.

BM25 provides lexical/exact-term matching.

The cross-encoder then evaluates the question and candidate chunk together to improve final ordering.

---

# Tool Calling Architecture

Week 9 exposes application capabilities to the LLM as tools.

Current tools:

1. `search_documents`
2. `get_workspace_stats`
3. `web_search`

The intended execution model is:

```text
                    User Question
                          ↓
                     Agent / LLM
                          ↓
                 Need a tool?
                  /           \
                No             Yes
                ↓               ↓
               LLM          Structured
                ↓           Tool Call
             Answer              ↓
                              Tool Node
                                 ↓
                         Execute Tool Safely
                                 ↓
                            Tool Result
                                 ↓
                                LLM
                                 ↓
                           Final Answer
```

The LLM does not directly execute Python functions.

Instead:

```text
LLM
 ↓
Tool Name + Arguments
 ↓
Application validates call
 ↓
Application executes tool
 ↓
Tool result
 ↓
LLM
 ↓
Natural-language answer
```

## `search_documents`

Reuses the existing RAG pipeline:

```text
search_documents
       ↓
RAGService
       ↓
Hybrid Retrieval
       ↓
Cross-Encoder Reranking
       ↓
Structured Results
```

## `get_workspace_stats`

Provides safe, read-only application statistics:

```text
get_workspace_stats
       ↓
Repository Queries
       ↓
PostgreSQL
       ↓
Structured Statistics
```

It does not allow arbitrary SQL generated by the LLM.

## `web_search`

Provides external web search:

```text
web_search
    ↓
Search API
    ↓
External Web
    ↓
Normalized Results
    ↓
LLM
```

The final Week 9 architecture will add a centralized registry:

```text
Tool Registry
 ├── search_documents
 ├── get_workspace_stats
 └── web_search
```

This registry is intended to make tool discovery and execution independent from the core agent logic.

---

# Project Structure

Current repository structure:

```text
ai-knowledge-assistant/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth/
│   │   │   │   ├── router.py
│   │   │   │   └── schemas.py
│   │   │   ├── conversations/
│   │   │   │   ├── router.py
│   │   │   │   └── schemas.py
│   │   │   └── documents/
│   │   │       ├── router.py
│   │   │       └── schemas.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── dependencies.py
│   │   │
│   │   ├── database/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   │
│   │   ├── graph/
│   │   │   ├── state.py
│   │   │   ├── graph.py
│   │   │   └── nodes/
│   │   │       ├── chatbot.py
│   │   │       └── rag.py
│   │   │
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   ├── document.py
│   │   │   └── document_chunk.py
│   │   │
│   │   ├── rag/
│   │   │   ├── extractor.py
│   │   │   ├── chunker.py
│   │   │   ├── embedder.py
│   │   │   ├── retriever.py
│   │   │   ├── query_rewriter.py
│   │   │   ├── context_builder.py
│   │   │   ├── prompt_builder.py
│   │   │   ├── citation_builder.py
│   │   │   ├── bm25_retriever.py
│   │   │   ├── hybrid_retriever.py
│   │   │   └── cross_encoder_reranker.py
│   │   │
│   │   ├── repositories/
│   │   │   ├── user_repository.py
│   │   │   ├── conversation_repository.py
│   │   │   ├── message_repository.py
│   │   │   ├── document_repository.py
│   │   │   └── document_chunk_repository.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── conversation.py
│   │   │   └── message.py
│   │   │
│   │   └── services/
│   │       ├── auth_service.py
│   │       ├── chat_service.py
│   │       ├── document_service.py
│   │       ├── rag_service.py
│   │       └── gemini_service.py
│   │
│   ├── alembic/
│   │   └── versions/
│   │
│   ├── uploads/
│   ├── alembic.ini
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   ├── layout/
│   │   │   └── upload/
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   └── ChatPage.jsx
│   │   ├── services/
│   │   │   ├── api.js
│   │   │   ├── authService.js
│   │   │   ├── conversationService.js
│   │   │   └── documentService.js
│   │   ├── App.jsx
│   │   ├── Layout.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── docs/
├── CODEBASE_STRUCTURE.md
├── STREAMING_IMPLEMENTATION.md
├── .env.example
├── .gitignore
└── README.md
```

Week 9 is currently extending the backend with a tools layer.

Expected direction:

```text
backend/app/tools/
```

with the three Week 9 tools and a centralized registry.

---

# Technology Stack

| Layer | Technology | Status |
|---|---|---|
| Frontend | React + JavaScript + Vite | Implemented |
| Styling | Plain CSS | Implemented |
| HTTP Client | Axios | Implemented |
| Backend | FastAPI + Python | Implemented |
| ORM | SQLAlchemy 2.0 | Implemented |
| Migrations | Alembic | Implemented |
| Authentication | JWT + bcrypt/passlib | Implemented |
| Database | PostgreSQL 16 | Implemented |
| Vector Search | pgvector | Implemented |
| Vector Index | HNSW | Implemented |
| LLM | Gemini Flash | Implemented |
| Agent Orchestration | LangGraph | Implemented |
| RAG | Semantic + BM25 + Hybrid + Cross-Encoder | Implemented |
| Query Rewriting | Gemini-based | Implemented |
| Streaming | SSE / EventSource | Implemented |
| Web Search | Tavily API | Week 9 |
| Tool Calling | LLM + LangGraph | In progress |
| MCP | Model Context Protocol | Week 9.5 planned |
| Redis | Redis 7 | Week 15 planned |
| Evaluation | RAGAS | Week 14 planned |
| Observability | LangSmith | Week 14 planned |
| Containers | Docker + Compose | Week 16 planned |
| CI/CD | GitHub Actions | Week 17 planned |
| Cloud | AWS ECS + RDS + S3 | Week 17 planned |

---

# Implemented Features

## Chat

- Conversational AI
- Conversation persistence
- Message persistence
- Conversation management
- Gemini responses
- Streaming responses

## Authentication

- User registration
- Login
- JWT access tokens
- Protected endpoints
- Password hashing

## Documents

- PDF upload
- DOCX upload
- TXT upload
- Document listing
- Document deletion
- Local file storage
- Document metadata persistence

## RAG

- Text extraction
- Recursive chunking
- Chunk overlap
- Gemini embeddings
- 768-dimensional vectors
- PostgreSQL pgvector
- HNSW indexing
- Semantic retrieval
- Query rewriting
- BM25 retrieval
- Hybrid retrieval
- Candidate deduplication
- Cross-encoder reranking
- Context construction
- Grounded prompting
- Source citation generation

## Tool Calling

Currently implemented tool capabilities:

- Document search
- Workspace statistics
- Web search

The complete LLM-driven tool loop is still being completed.

---

# API Endpoints

## Authentication

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

## Conversations

```text
GET    /api/conversations
POST   /api/conversations
PATCH  /api/conversations/{id}
DELETE /api/conversations/{id}

GET  /api/conversations/{id}/messages
POST /api/conversations/{id}/messages
POST /api/conversations/{id}/messages/stream
```

## Documents

```text
POST   /api/documents/upload
GET    /api/documents
DELETE /api/documents/{id}
```

Additional future endpoints include evaluation and knowledge-base APIs.

---

# Database

The current application uses PostgreSQL with pgvector.

Core relationships:

```text
users
  │
  ├── conversations
  │       │
  │       └── messages
  │
  └── documents
          │
          └── document_chunks
```

The vector-enabled chunk table contains:

```text
document_id
chunk_text
chunk_index
embedding VECTOR(768)
metadata JSONB
created_at
```

The embedding column is indexed using an HNSW index with cosine-distance operations.

Future tables include:

```text
user_memory
evaluations
```

A future knowledge-base grouping layer is also planned.

---

# Local Setup

## Prerequisites

Install:

- Python 3.x
- Node.js / npm
- PostgreSQL 16
- PostgreSQL pgvector extension
- Git

You also need API credentials for the services used by the application, especially Gemini and Tavily.

---

## 1. Clone the Repository

```bash
git clone <your-repository-url>
cd ai-knowledge-assistant
```

---

## 2. Backend Setup

Enter the backend:

```bash
cd backend
```

Create and activate a virtual environment.

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
```

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 3. Configure Environment Variables

Create:

```text
backend/.env
```

Use the project's `.env.example` as the template.

Typical configuration includes:

```text
DATABASE_URL=...
GEMINI_API_KEY=...
TAVILY_API_KEY=...
JWT_SECRET_KEY=...
```

Do not commit real secrets to Git.

---

## 4. PostgreSQL Setup

Create the application database and ensure pgvector is available.

The application uses:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Run database migrations:

```bash
alembic upgrade head
```

From the `backend` directory.

---

# Running the Application

You normally run the backend and frontend in separate terminals.

## Terminal 1 — Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

On Windows PowerShell:

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The FastAPI application should then be available at:

```text
http://127.0.0.1:8000
```

FastAPI's interactive API documentation is normally available at:

```text
http://127.0.0.1:8000/docs
```

---

## Terminal 2 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite will display the local frontend URL, normally similar to:

```text
http://localhost:5173
```

Open that address in the browser.

---

# Development Workflow

The project is intentionally developed incrementally.

The preferred workflow is:

```text
Understand
   ↓
Design
   ↓
Implement
   ↓
Unit / validation test
   ↓
Integrate
   ↓
End-to-end test
   ↓
Document
   ↓
Commit
```

For each major feature:

1. Understand the existing architecture.
2. Avoid rewriting working components.
3. Add one responsibility at a time.
4. Keep services and repositories separated.
5. Validate components independently.
6. Integrate only after the isolated component works.
7. Run the complete flow.
8. Update documentation.

---

# Week-by-Week Evolution

## Week 1 — Foundation

```text
React
 +
FastAPI
 +
Gemini
 +
LangGraph
```

Initial flow:

```text
User
 ↓
FastAPI
 ↓
LangGraph
 ↓
Chatbot
 ↓
Gemini
 ↓
Answer
```

---

## Week 2 — Persistence

Added:

- PostgreSQL
- SQLAlchemy
- Alembic
- Users
- Conversations
- Messages
- Repository pattern
- Conversation history

---

## Week 3 — Streaming

Added:

```text
Gemini Streaming
      ↓
FastAPI
      ↓
SSE
      ↓
React
```

The frontend progressively renders assistant responses.

---

## Week 4 — Authentication

Added:

```text
Registration
Login
 ↓
JWT
 ↓
Protected APIs
```

Passwords are stored using secure password hashing rather than plaintext.

---

## Week 5 — Conversation Management

Expanded the chat experience with persistent conversation listing and management.

---

## Week 6 — Documents

Added:

```text
Upload
 ↓
DocumentService
 ↓
Document Persistence
```

Supported formats:

```text
PDF
DOCX
TXT
```

---

## Week 7 — RAG Foundation

Added:

```text
Extract
 ↓
Chunk
 ↓
Embed
 ↓
pgvector
 ↓
Semantic Retrieval
```

This was the first complete document-grounded retrieval foundation.

---

## Week 8 — Advanced RAG

The retrieval architecture became:

```text
Query Rewriting
      ↓
Semantic + BM25
      ↓
Hybrid Retrieval
      ↓
Cross-Encoder Reranking
      ↓
Context Builder
      ↓
Grounded Prompt
      ↓
Gemini
      ↓
Source Citations
```

Week 8 transformed basic retrieval into a multi-stage RAG pipeline.

---

## Week 9 — Tool Calling

Current objective:

```text
LLM
 ↓
Structured Tool Call
 ↓
Conditional Routing
 ↓
Tool Execution
 ↓
Tool Result
 ↓
LLM
 ↓
Final Answer
```

Tools:

```text
search_documents
get_workspace_stats
web_search
```

Current progress is through the implementation of the three individual tools; the centralized registry and full LLM/LangGraph tool loop are next.

---

# Future Roadmap

## Week 9 — Complete Tool Calling

Remaining:

```text
Tool Registry
      ↓
LLM Tool Binding
      ↓
Structured Tool Calls
      ↓
Conditional LangGraph Routing
      ↓
Tool Node
      ↓
Tool Result → LLM
      ↓
Final Answer
      ↓
End-to-End Validation
```

---

## Week 9.5 — MCP

Replace or evolve the hand-written tool integration toward the Model Context Protocol.

Future architecture:

```text
LangGraph
    ↓
MCP Client
    ↓
MCP Servers
    ├── Web Search
    ├── Filesystem
    └── Custom Tools
```

MCP is intentionally separated from Week 9 so the underlying tool-calling concepts are understood first.

---

## Week 10 — Full Router Agent

Introduce intent classification:

```text
                    User Query
                         ↓
                      Router
                         ↓
       ┌─────────┬───────┼─────────┐
       ↓         ↓       ↓         ↓
      Chat      RAG     Tool     Memory
       └─────────┴───────┴─────────┘
                         ↓
                  Context Builder
                         ↓
                       LLM
                         ↓
                    Evaluation
                         ↓
                    Save Memory
```

---

## Week 11 — Multi-Agent System

Introduce a supervisor pattern:

```text
                 Supervisor
                /     |      \
               ↓      ↓       ↓
          Researcher Writer Reviewer
               \      |       /
                └─────┴───────┘
                       ↓
                  Supervisor
                       ↓
                     Finish
```

The goal is to demonstrate specialist agents coordinated by a supervisor rather than one monolithic agent.

---

## Week 12 — Long-Term Memory

Introduce persistent user memories.

Conceptually:

```text
Conversation
     ↓
Fact Extraction
     ↓
Memory Service
     ↓
user_memory
     ↓
Future Conversations
```

The assistant will be able to use relevant user preferences/facts across sessions.

---

## Week 13 — LangChain / LCEL

Introduce LangChain LCEL where it provides value after the lower-level implementations have already been understood.

This follows the project's learning philosophy:

```text
Understand the mechanism first
          ↓
Use abstraction later
```

---

## Week 14 — Evaluation + Observability

Introduce:

- RAGAS
- Faithfulness
- Answer relevance
- Context precision
- Context recall
- Groundedness
- LangSmith tracing
- Evaluation dashboard

Future flow:

```text
Question
 ↓
RAG / Agent
 ↓
Answer
 ↓
RAGAS
 ↓
Evaluation Scores
 ↓
Dashboard
```

The purpose is to measure system quality rather than relying only on subjective testing.

---

## Week 15 — Redis

Introduce Redis for:

- Session-related caching
- Rate limiting
- Performance improvements

Architecture:

```text
FastAPI
  ↓
Redis
  ├── Cache
  └── Rate Limit
  ↓
PostgreSQL
```

---

## Week 16 — Docker

Containerize the system:

```text
Docker Compose
 ├── Frontend
 ├── Backend
 └── PostgreSQL
```

The objective is a reproducible development environment.

---

## Week 17 — CI/CD + AWS

Target deployment architecture:

```text
GitHub
   ↓
GitHub Actions
   ↓
Docker Build
   ↓
AWS
 ├── ECS
 ├── RDS PostgreSQL
 └── S3
```

The final goal is to move from a local portfolio project toward a deployable production-oriented system.

---

# Long-Term Target Architecture

After the roadmap is complete, the target architecture is approximately:

```text
                           React
                             │
                         HTTP / SSE
                             │
                             ▼
                          FastAPI
                             │
                       Auth / APIs
                             │
                             ▼
                        ChatService
                             │
                             ▼
                         LangGraph
                             │
                             ▼
                          Router
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
             RAG           Tools          Memory
              │              │              │
              │            MCP              │
              │              │              │
              └──────────────┼──────────────┘
                             ↓
                     Context Builder
                             │
                             ▼
                            LLM
                             │
                  ┌──────────┴──────────┐
                  ↓                     ↓
               Response             Evaluation
                  │                     │
                  ↓                     ↓
              PostgreSQL              RAGAS
                  │
             pgvector
                  │
                Redis
                  │
                AWS
```

---

# Architecture Principles

The project follows several consistent design principles.

## Separation of Concerns

Each layer owns a specific responsibility:

```text
API
 ↓
Service
 ↓
Repository / RAG / Tool
 ↓
Database / External API
```

---

## Single Responsibility

Examples:

```text
QueryRewriter
    → rewrites queries

SemanticRetriever
    → vector retrieval

BM25Retriever
    → lexical retrieval

HybridRetriever
    → combines candidates

CrossEncoderReranker
    → reranks candidates

ContextBuilder
    → formats context

PromptBuilder
    → builds prompts

CitationBuilder
    → builds source references
```

---

## Dependency Injection

Components are passed their dependencies rather than constructing the entire application graph internally.

For example:

```text
RAGService
 ├── HybridRetriever
 ├── CrossEncoderReranker
 └── ContextBuilder
```

This keeps components testable and replaceable.

---

## Structured State

LangGraph uses a shared state object to carry information through the workflow.

Conceptually:

```text
AgentState
 ├── query
 ├── messages
 ├── conversation_history
 ├── retrieved_docs
 ├── rewritten_query
 ├── context
 ├── prompt
 ├── sources
 └── tool_results
```

Future state additions will support:

```text
intent
user_memories
final_context
eval_scores
is_grounded
```

---

## Safe Tool Execution

The LLM should never directly execute arbitrary application operations.

The intended model is:

```text
LLM
 ↓
Structured Tool Call
 ↓
Application Validation
 ↓
Known Tool
 ↓
Safe Execution
 ↓
Structured Result
```

For example, workspace statistics use predefined repository queries rather than allowing:

```text
LLM → arbitrary SQL
```

---

# Interview-Level Explanation

A concise way to explain the project:

> I built a production-oriented AI Knowledge Assistant using React, FastAPI, PostgreSQL, pgvector, Gemini, and LangGraph. The system supports conversational chat, document ingestion, semantic and hybrid retrieval, cross-encoder reranking, grounded generation, source citations, and streaming responses. I am currently extending the LangGraph workflow with LLM-driven tool calling, where the model produces a structured tool call, conditional graph routing sends it to a safe tool executor, the result is returned to the model, and the model produces the final answer.

For the RAG architecture:

> I use a two-stage retrieval pipeline. Semantic vector search and BM25 generate a broad candidate pool, then a cross-encoder reranks the candidates for better relevance. The final chunks are passed through context and prompt builders to generate a grounded response, with citations derived from the retrieved metadata.

For tool calling:

> The LLM does not directly execute application functions. It receives tool definitions and decides whether a tool is needed. It generates a structured tool call with the tool name and arguments. The application validates and executes that tool through a controlled tool layer, stores the result in graph state, and passes it back to the LLM for final answer generation.

---

# Project Philosophy

This project is intentionally built week-by-week.

The goal is not simply to produce a large codebase.

The goal is to understand how each layer works:

```text
Raw LLM API
     ↓
LangGraph
     ↓
RAG
     ↓
Advanced RAG
     ↓
Tool Calling
     ↓
MCP
     ↓
Routing
     ↓
Multi-Agent
     ↓
Memory
     ↓
Evaluation
     ↓
Production Infrastructure
```

Each new abstraction is introduced after understanding the lower-level mechanism.

That makes the final system easier to reason about, debug, test, and explain in technical interviews.

---

# Current Next Step

The immediate next implementation milestone is:

```text
Week 9 — Part 5
        ↓
Tool Registry
        ↓
Register:
  • search_documents
  • get_workspace_stats
  • web_search
```

After the registry is working:

```text
Part 6
LLM Tool Calling
        ↓
Part 7
LangGraph Tool Node
        ↓
Part 8
End-to-End Tool Loop
        ↓
WEEK 9 COMPLETE
```
