# Current Status Report

## Project Snapshot
- Current week: Week 7
- Current branch: suraj_Ofc
- Overall progress: Weeks 1–6 are implemented at the core feature level, with the project now covering basic chat, persistence, streaming, authentication, conversation history, document upload, and semantic retrieval over document chunks.

---

## Week 1 — Simple AI Chat
- Current week: Week 1 (Completed)
- Completed work: Built the initial end-to-end chat flow using React on the frontend and FastAPI on the backend. The app can send a user message to the Gemini model and display the AI response.
- Current branch: suraj_Ofc
- Working features: Basic chat UI, message display, Gemini-powered response generation.
- APIs: GET /health, POST /api/conversations/{conversation_id}/messages
- Database status: No persistent chat storage yet; this week focused on the basic AI interaction loop.
- Known issues: No message history, no conversation persistence, and no proper chat state management beyond the UI.
- Next task: Add conversation and message persistence so chats survive refreshes.

---

## Week 2 — Memory and Conversation History
- Current week: Week 2 (Completed)
- Completed work: Added persistent chat storage using PostgreSQL and SQLAlchemy. The system now supports users, conversations, and messages with relational tables and migration-based schema setup.
- Current branch: suraj_Ofc
- Working features: Conversation creation, message saving, retrieval of prior messages for context, and conversation history support.
- APIs: GET /api/conversations, POST /api/conversations, GET /api/conversations/{conversation_id}/messages
- Database status: Alembic migrations are in place for users, conversations, and messages; timestamps, mode, and source fields were added in later schema updates.
- Known issues: Context use is still simple and limited to recent history rather than a full memory system.
- Next task: Introduce streaming text responses for a more interactive experience.

---

## Week 3 — Streaming Responses
- Current week: Week 3 (Completed)
- Completed work: Implemented streaming chat responses so the assistant text appears incrementally instead of waiting for the full reply. The frontend consumes streamed chunks in real time.
- Current branch: suraj_Ofc
- Working features: Real-time typing-like response rendering, dynamic message updates during generation.
- APIs: POST /api/conversations/{conversation_id}/messages/stream
- Database status: User messages are stored immediately and the final assistant response is saved after streaming completes.
- Known issues: Streaming is currently implemented as plain text chunks with basic error handling; there is no advanced stream control or cancellation flow yet.
- Next task: Protect routes with authentication and tie chats to specific users.

---

## Week 4 — Authentication
- Current week: Week 4 (Completed)
- Completed work: Added user registration, login, JWT-based authentication, and protected access to chat-related endpoints. Each user can now own and access their own conversations.
- Current branch: suraj_Ofc
- Working features: Register and login flow, protected routes, authenticated user profile endpoint.
- APIs: POST /api/auth/register, POST /api/auth/login, GET /api/auth/me
- Database status: Users table includes password hashes, timestamps, and unique email constraints; chat routes now resolve the authenticated user.
- Known issues: Token refresh and stronger auth UX improvements are not implemented yet.
- Next task: Build a proper conversation sidebar for browsing, renaming, and deleting chats.

---

## Week 5 — Chat History Sidebar
- Current week: Week 5 (Completed)
- Completed work: Implemented a chat history experience with a sidebar that lists previous conversations, allows switching between chats, and supports rename and delete actions.
- Current branch: suraj_Ofc
- Working features: Sidebar conversation list, chat switching, conversation rename, conversation deletion, auto-refresh after actions.
- APIs: GET /api/conversations, POST /api/conversations, PATCH /api/conversations/{conversation_id}, DELETE /api/conversations/{conversation_id}
- Database status: Conversations are now tied to users and ordered by recent updates; messages remain connected to their conversation records.
- Known issues: Conversation title generation is basic, and some UI refresh behavior can be refined for smoother state handling.
- Next task: Add file upload and document management support.

---

## Week 6 — File Upload
- Current week: Week 6 (Completed)
- Completed work: Implemented document upload, listing, and deletion. Users can upload PDF, DOCX, and TXT files, which are stored locally under the uploads directory and tracked in the database.
- Current branch: suraj_Ofc
- Working features: File picker in the UI, upload progress feedback, document listing, delete action, metadata persistence.
- APIs: POST /api/documents/upload, GET /api/documents, DELETE /api/documents/{document_id}
- Database status: The documents table is present with user ownership, metadata, file path, file type, size, and upload timestamp.
- Known issues: File upload remains storage-based only; content-based retrieval and embedding support are still incomplete.
- Next task: Transition to Week 7 and implement basic semantic retrieval using embedded document chunks.

---

## Week 7 — RAG Foundation
- Current week: Week 7 (Current)
- Completed work: Built the core Retrieval-Augmented Generation (RAG) foundation by implementing document chunking, embedding generation, pgvector-based vector storage, semantic retrieval, and LangGraph integration for document retrieval.
- Current branch: suraj_Ofc
- Working features:
  - Uploaded documents are automatically processed into searchable knowledge.
  - `DocumentService` now delegates document processing and indexing to a dedicated `RAGService`.
  - Document text is extracted from PDF, DOCX, and TXT files.
  - Documents are split into overlapping chunks using a dedicated `DocumentChunker`.
  - Each chunk is converted into a 768-dimensional embedding using `GeminiEmbedder`.
  - Chunks and embeddings are stored in PostgreSQL using pgvector with an HNSW vector index.
  - `SemanticRetriever` converts user questions into embeddings and retrieves the top-k most relevant document chunks using cosine similarity search.
  - A dedicated LangGraph RAG node retrieves relevant document chunks and stores them in the graph state (`retrieved_docs`) for downstream processing.
- APIs: No new public API endpoints were introduced. RAG processing is integrated into the backend document processing pipeline and LangGraph workflow.
- Database status:
  - `document_chunks` table stores chunk text, embeddings, metadata, and document relationships.
  - pgvector extension is enabled.
  - HNSW vector index (`idx_chunks_embedding`) accelerates cosine similarity search.
  - Uploaded documents are automatically indexed after upload and marked as `processed`.
- Known issues:
  - Retrieved document context is now available in the LangGraph state, but it is not yet injected into the LLM prompt.
  - Source citations and grounded response generation have not yet been implemented.
- Next task:
  - Build the RAG service to coordinate retrieval operations.
  - Inject retrieved document context into the LLM prompt.
  - Generate grounded responses using retrieved document chunks.
  - Add source citations to AI responses.