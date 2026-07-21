You can add the following to your Week 7 documentation.

---

# Week 7 — RAG Foundation

User uploads PDF
        │
        ▼
Store file in uploads/
        │
        ▼
Read file text
        │
        ▼
Split into chunks
        │
        ▼
Generate embedding for each chunk
        │
        ▼
Insert one row per chunk into document_chunks
        │
        ▼
HNSW index updates automatically
──────────────────────────────────────
        │
User asks a question
        │
        ▼
Generate question embedding
        │
        ▼
HNSW similarity search (by comparing similar embadings )
        │
        ▼
Top 5 relevant chunks
        │
        ▼
Send chunks + question to Gemini
        │
        ▼
Grounded answer

## Part 1 — Enable pgvector Extension ✅ (Completed)

### Objective

Prepare the PostgreSQL database to store vector embeddings required for semantic search and Retrieval-Augmented Generation (RAG).

### Work Completed

* Verified the PostgreSQL server version being used by the project.
* Identified that the project database is running on **PostgreSQL 14.23**.
* Checked whether the `vector` extension was available using:

```sql
SELECT *
FROM pg_available_extensions
WHERE name = 'vector';
```

* Initially confirmed that the `vector` extension was not available.
* Installed the **pgvector** extension package for PostgreSQL 14 on Ubuntu.
* Verified that the extension became available:

```sql
SELECT *
FROM pg_available_extensions
WHERE name = 'vector';
```

Result:

```
name: vector
default_version: 0.8.4
installed_version:
comment: vector data type and ivfflat and hnsw access methods
```

* Enabled the extension for the `ai_knowledge_assistant` database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

* Verified successful installation by confirming that the `vector` extension appears under the database **Extensions** in pgAdmin.

### Outcome

The project database is now configured to use the PostgreSQL `vector` data type. This provides the foundation required for storing embedding vectors, performing similarity searches, and implementing the RAG pipeline in the upcoming parts of Week 7.

### Status

**✅ Part 1 Completed**


---------------------------------------------------------------------------------------------------------------------------------------------------------------------------



--

# Part 2 — Create `document_chunks` Table ✅

## Objective

Create the database schema required to store document chunks and their vector embeddings. This provides the storage layer for semantic search and Retrieval-Augmented Generation (RAG).

---

## Work Completed

### 1. Created the `DocumentChunk` SQLAlchemy Model

Added a new `DocumentChunk` model containing:

* UUID primary key (`id`)
* Foreign key (`document_id`) referencing the `documents` table
* `chunk_text` column to store the text of each document chunk
* `chunk_index` column to preserve the order of chunks within a document
* `embedding` column using the PostgreSQL `VECTOR(768)` data type
* `metadata` JSON column for storing chunk-related metadata
* `created_at` timestamp for recording when the chunk was created

---

### 2. Added ORM Relationships

Established a bidirectional relationship between `Document` and `DocumentChunk`.

* Added a `chunks` relationship to the `Document` model.
* Added a `document` relationship to the `DocumentChunk` model.
* Configured cascading delete so that deleting a document automatically removes all associated document chunks.

---

### 3. Registered the Model

Registered the new `DocumentChunk` model within the application's model imports so that SQLAlchemy and Alembic include it in the metadata during migration generation.

---

### 4. Generated Alembic Migration

Generated a new Alembic migration for the `document_chunks` table using:

```bash
alembic revision --autogenerate -m "create document_chunks table"
```

Reviewed the generated migration before applying it to the database.

---

### 5. Applied Database Migration

Executed:

```bash
alembic upgrade head
```

to create the `document_chunks` table in the PostgreSQL database.

---

### 6. Added HNSW Vector Index

Created a separate Alembic migration to add an HNSW index on the `embedding` column.

The index was created using:

* `USING hnsw`
* `vector_cosine_ops`
* `m = 16`
* `ef_construction = 64`

This enables efficient approximate nearest-neighbor (ANN) searches for vector similarity.

---

### 7. Verified Database Schema

Verified the successful creation of:

* `document_chunks` table
* All table columns
* Foreign key relationship
* `VECTOR(768)` embedding column
* `document_id` index
* HNSW vector index (`idx_chunks_embedding`)

using PostgreSQL system catalog queries.

---

## Database Status

Added a new `document_chunks` table containing:

* `id`
* `document_id`
* `chunk_text`
* `chunk_index`
* `embedding`
* `metadata`
* `created_at`

Created the following indexes:

* `document_chunks_pkey`
* `ix_document_chunks_document_id`
* `idx_chunks_embedding` (HNSW vector index)

---

## Outcome

The project database is now prepared to store document chunks and their embedding vectors. The schema and HNSW vector index required for semantic similarity search are in place. The next step is to populate this table by extracting document text, generating chunks, creating embeddings, and storing them during document processing.

---

## Status

**✅ Part 2 Completed**


---------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# Part 3 — Embedding Generation ✅

## Objective

Implement the embedding generation component responsible for converting text into dense vector embeddings using Google's Gemini embedding model. These embeddings will later be stored in the `document_chunks` table and used for semantic similarity search in the RAG pipeline.

---

## Work Completed

### 1. Learned the Embedding Workflow

Understood the role of embeddings within the Retrieval-Augmented Generation (RAG) pipeline.

Covered the following concepts:

* What embeddings are
* Difference between text generation models and embedding models
* Semantic representation of text as vectors
* Vector dimensions
* Semantic similarity search
* How embeddings enable document retrieval beyond traditional keyword matching

---

### 2. Selected the Embedding Model

Selected Google's **Gemini Embedding** model:

```text
gemini-embedding-001
```

Configured the model to generate **768-dimensional** embeddings by specifying:

```python
config={
    "output_dimensionality": 768,
}
```

Using 768 dimensions keeps the generated embeddings compatible with the project's existing PostgreSQL `VECTOR(768)` column in the `document_chunks` table.

---

### 3. Installed and Verified the Google Gen AI SDK

Installed the latest Google Gen AI Python SDK:

```bash
pip install google-genai
```

Verified the installation by:

* Confirming the package installation
* Importing:

```python
from google import genai
```

* Successfully creating a Google Gen AI client

This confirmed that the project environment was correctly configured for embedding generation.

---

### 4. Created the Embedder Module

Created:

```text
backend/app/rag/embedder.py
```

This module serves as the dedicated embedding generation component for the RAG pipeline.

---

### 5. Implemented the `GeminiEmbedder` Class

Created a reusable `GeminiEmbedder` class responsible for all embedding-related operations.

Responsibilities include:

* Initializing the Google Gen AI client
* Reusing the application's existing Gemini API configuration
* Sending text to the embedding model
* Returning embedding vectors

This separates embedding logic from document processing and retrieval logic.

---

### 6. Reused Existing Project Configuration

Integrated the embedder with the project's existing configuration system.

The Google Gen AI client is initialized using:

```python
settings.GEMINI_API_KEY
```

loaded from the application's environment variables.

No additional configuration files or API key management were required.

---

### 7. Implemented the `generate_embedding()` Method

Added the `generate_embedding()` method to convert a single text input into an embedding vector.

The method performs the following steps:

* Accepts a text string
* Sends the text to the `gemini-embedding-001` model
* Requests a 768-dimensional embedding
* Extracts the embedding values from the API response
* Returns the embedding as a Python `list[float]`

---

### 8. Added Embedding Dimension Validation

Implemented validation to ensure that every generated embedding contains exactly **768 dimensions**.

If the returned embedding size does not match the expected dimension, a `ValueError` is raised.

This guarantees compatibility with the PostgreSQL `VECTOR(768)` column and helps detect unexpected API or configuration changes.

---

### 9. Added Error Handling

Wrapped the embedding API call in a `try-except` block.

If embedding generation fails due to API errors, authentication issues, or network failures, the method raises a descriptive `RuntimeError`.

This provides clearer application-level error reporting during document processing.

---

### 10. Created a Standalone Test

Created:

```text
backend/test_embedder.py
```

to independently verify the embedding generation component.

The test:

* Creates a `GeminiEmbedder` instance
* Generates an embedding for sample text
* Prints the embedding dimension
* Prints the first few embedding values

This confirmed that the embedder functions correctly before integrating it into the RAG indexing pipeline.

---

## Outcome

The project now includes a fully functional embedding generation component capable of converting text into **768-dimensional vector embeddings** using Google's Gemini embedding model. These embeddings are returned as Python lists and are ready to be stored in the PostgreSQL `document_chunks` table for semantic search and Retrieval-Augmented Generation (RAG).

---

## Status

**✅ Part 3 Completed**



Uploaded Document
        │
        ▼
Extract Text        (already have file upload)
        │
        ▼
Chunker             ← Part 4
        │
        ▼
Chunk List
        │
        ▼
Embedder            ← Part 3
        │
        ▼
Database            ← Part 5




---------------------------------------------------------------------------------------------------------------------------------------------------------------------------


Yes. Based on everything we've actually implemented (without assuming extra features), here's a detailed and accurate write-up for **Week 7 – Part 4**.

---

# Part 4 — Document Chunking & Document Processing Pipeline ✅

## Objective

Implement the document processing pipeline responsible for converting uploaded documents into searchable knowledge.

This stage extends the document upload functionality by extracting text from uploaded files, splitting the text into manageable chunks, generating embeddings for each chunk, and storing the processed data in the `document_chunks` table. This forms the indexing pipeline required for Retrieval-Augmented Generation (RAG).

---

## Work Completed

### 1. Created the Document Chunker Module

Created:

```text
backend/app/rag/chunker.py
```

Implemented a dedicated `DocumentChunker` component responsible for splitting extracted document text into smaller chunks suitable for embedding generation and semantic retrieval.

This separates document chunking logic from the document service and keeps the RAG pipeline modular.

---

### 2. Configured Recursive Character Text Splitting

Implemented LangChain's:

```python
RecursiveCharacterTextSplitter
```

Configured with:

* **Chunk Size:** `1000` characters
* **Chunk Overlap:** `200` characters

This configuration preserves contextual continuity between adjacent chunks while ensuring that each chunk remains within the optimal size for embedding generation.

---

### 3. Introduced a Dedicated Chunk Data Model

Instead of returning plain strings, introduced a structured `Chunk` dataclass.

Each generated chunk now contains:

* `chunk_index`
* `chunk_text`
* `metadata`

This provides a richer representation of each document chunk and simplifies later processing steps.

Example:

```python
Chunk(
    chunk_index=0,
    chunk_text="...",
    metadata={
        "char_start": ...,
        "char_end": ...
    }
)
```

---

### 4. Generated Chunk Metadata

Enhanced the chunking process by calculating metadata for every generated chunk.

For each chunk the following metadata is generated:

* Starting character position (`char_start`)
* Ending character position (`char_end`)

The character offsets are calculated using the actual location of each chunk within the original document rather than estimating positions.

This metadata provides traceability between stored chunks and the original document.

---

### 5. Added Chunk Validation

Implemented validation to improve robustness.

Handled:

* Empty document content
* Failure to locate a generated chunk within the original document

If a chunk cannot be mapped back to the original document text, a descriptive exception is raised.

---

### 6. Created the Document Extraction Module

Created:

```text
backend/app/rag/extractor.py
```

Introduced a dedicated `DocumentExtractor` responsible for extracting plain text from uploaded documents before chunking.

The extractor isolates file parsing logic from the document service.

---

### 7. Implemented Multi-format Document Extraction

Implemented support for extracting text from the following document formats:

#### PDF

Used:

```python
pypdf.PdfReader
```

Features:

* Reads every page in the PDF
* Extracts text from each page
* Combines page contents into a single text string
* Validates that extractable text exists
* Handles extraction failures with descriptive exceptions

---

#### DOCX

Used:

```python
python-docx
```

Features:

* Reads document paragraphs
* Ignores empty paragraphs
* Preserves paragraph boundaries
* Returns a single combined text string
* Validates extracted content

---

#### TXT

Implemented plain text extraction using:

```python
Path.read_text()
```

Features:

* Reads UTF-8 encoded text files
* Validates non-empty content
* Provides consistent error handling

---

### 8. Built the Document Processing Pipeline

Extended `DocumentService` by implementing:

```python
process_document()
```

This method orchestrates the complete indexing workflow after a document has been uploaded.

The processing sequence is:

```
Uploaded Document
        ↓
Extract Text
        ↓
Chunk Text
        ↓
Generate Embeddings
        ↓
Create Chunk Records
        ↓
Store in Database
        ↓
Update Document Status
```

The service delegates each responsibility to the appropriate component rather than implementing the logic directly.

---

### 9. Integrated the Existing Embedder

Reused the previously implemented:

```text
GeminiEmbedder
```

For every generated chunk:

* Generated a 768-dimensional embedding
* Associated the embedding with the corresponding chunk
* Prepared the data for persistence in PostgreSQL

---

### 10. Created the DocumentChunk Repository

Created:

```text
backend/app/repositories/document_chunk_repository.py
```

Implemented repository methods for managing document chunks.

Implemented:

* `create()`
* `list_by_document()`
* `delete_by_document()`

This separates database operations from business logic and follows the repository pattern used throughout the project.

---

### 11. Stored Processed Chunks

For every generated chunk, created a `DocumentChunk` entity containing:

* Document ID
* Chunk index
* Chunk text
* Embedding vector
* Chunk metadata

Each chunk is then persisted into the `document_chunks` table.

---

### 12. Updated Document Processing Status

After successfully processing every chunk, the document status is updated from:

```
uploaded
```

to

```
processed
```

This indicates that the document has been completely indexed and is ready for semantic retrieval.

---

### 13. Integrated Processing with Document Upload

Updated the document upload workflow.

After successfully storing document metadata, the service now automatically invokes:

```python
process_document(document)
```

This means every uploaded document is immediately processed without requiring any manual indexing step.

The complete upload workflow is now:

```
Upload File
      ↓
Save File
      ↓
Save Document Metadata
      ↓
Extract Text
      ↓
Chunk Document
      ↓
Generate Embeddings
      ↓
Store Chunks
      ↓
Update Status
```

---

### 14. Verified the Complete Indexing Pipeline

Successfully tested the entire processing pipeline using uploaded TXT documents.

Verified:

* Document upload
* Text extraction
* Document chunking
* Embedding generation
* Storage of chunk records
* Storage of embedding vectors
* Preservation of chunk ordering
* Metadata generation
* Document status updated to `processed`

Database verification confirmed:

* Document successfully inserted into the `documents` table
* Multiple chunk records created in the `document_chunks` table
* Sequential `chunk_index` values
* Proper relationship between `documents` and `document_chunks`

---

## Outcome

The project now contains a complete document indexing pipeline capable of automatically processing uploaded documents into vectorized knowledge.

Each uploaded document is:

* Converted into plain text
* Split into context-preserving chunks
* Converted into semantic embeddings using the Gemini embedding model
* Stored in PostgreSQL together with metadata and document relationships

This establishes the complete ingestion layer required for Retrieval-Augmented Generation (RAG) and prepares the project for implementing semantic retrieval in the next stage.

---

## Status

**✅ Part 4 Completed**



----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# Part 5 — Semantic Retriever ✅

## Objective

Implement the semantic retrieval component responsible for finding the most relevant document chunks for a user's question.

This stage introduces vector-based retrieval by converting user questions into embeddings, performing cosine similarity search against the indexed document chunks stored in PostgreSQL, and returning the most relevant chunks. This establishes the retrieval layer required for Retrieval-Augmented Generation (RAG).

---

## Work Completed

### 1. Designed the Semantic Retrieval Flow

Studied and designed the end-to-end semantic retrieval pipeline used during question answering.

The implemented retrieval flow is:

```text
User Question
      ↓
Generate Query Embedding
      ↓
Cosine Similarity Search (pgvector)
      ↓
Top-K Relevant Chunks
      ↓
Return Retrieved Chunks
```

This retrieval pipeline complements the document indexing pipeline implemented in Part 4.

---

### 2. Extended the DocumentChunk Repository

Extended:

```text
backend/app/repositories/document_chunk_repository.py
```

by implementing:

```python
search_similar()
```

This repository method is responsible for performing semantic vector search within PostgreSQL.

Responsibilities include:

* Accepting a query embedding vector
* Performing cosine distance search using pgvector
* Ordering results by semantic similarity
* Limiting the number of returned chunks
* Returning matching database records

The repository remains responsible only for database interactions and does not perform embedding generation or business logic.

---

### 3. Implemented pgvector Cosine Distance Search

Implemented semantic vector retrieval using the pgvector SQLAlchemy integration.

Used:

```python
DocumentChunk.embedding.cosine_distance(...)
```

which generates PostgreSQL cosine distance queries internally.

The search query:

* Computes cosine distance between the query embedding and stored chunk embeddings
* Orders chunks by increasing cosine distance
* Returns the nearest semantic neighbours

This enables semantic retrieval without performing traditional keyword matching.

---

### 4. Leveraged the Existing HNSW Vector Index

The semantic search automatically utilizes the previously created HNSW index on the `embedding` column.

Since the index was configured using:

```text
vector_cosine_ops
```

no additional query optimization was required.

This allows efficient Approximate Nearest Neighbour (ANN) search even as the number of stored document chunks grows.

---

### 5. Built the SemanticRetriever Component

Created:

```text
backend/app/rag/retriever.py
```

Implemented the reusable:

```text
SemanticRetriever
```

component responsible for coordinating the retrieval workflow.

Its responsibilities include:

* Receiving a user's question
* Generating a query embedding
* Invoking the repository vector search
* Returning the retrieved document chunks

The retriever delegates embedding generation and database access to dedicated components rather than implementing those responsibilities itself.

---

### 6. Reused the Existing GeminiEmbedder

Integrated the previously implemented:

```text
GeminiEmbedder
```

to generate embeddings for user questions.

The retriever reuses the same embedding model (`gemini-embedding-001`) that was used during document indexing, ensuring that both document chunks and user queries exist within the same embedding space for meaningful semantic comparison.

---

### 7. Implemented Configurable Top-K Retrieval

Added configurable retrieval size by allowing callers to specify:

```python
top_k
```

The retriever now returns only the requested number of most relevant chunks.

The value is configurable and is not hardcoded, allowing future tuning of retrieval quality.

---

### 8. Introduced the RetrievedChunk Data Model

Introduced a dedicated:

```python
RetrievedChunk
```

dataclass representing retrieval results.

Each retrieved chunk contains:

* `document_id`
* `chunk_index`
* `chunk_text`
* `metadata`
* `cosine_distance`

This separates the application's retrieval layer from SQLAlchemy ORM models and provides a clean data structure for future LangGraph and LLM integration.

---

### 9. Added Retriever-Level Error Handling

Improved robustness by adding application-level error handling.

Handled:

* Embedding generation failures
* Database retrieval failures

Meaningful exceptions are raised while preserving the original underlying exception for debugging purposes.

---

### 10. Verified Semantic Retrieval

Created:

```text
backend/test_retriever.py
```

to independently test the retrieval pipeline.

The test:

* Creates a database session
* Initializes the repository
* Initializes the Gemini embedder
* Creates a `SemanticRetriever`
* Generates query embeddings
* Retrieves the most relevant chunks
* Prints cosine distance and retrieved chunk information

This confirmed that the semantic retrieval pipeline functions correctly before integrating it into LangGraph.

---

### 11. Validated Retrieval Quality

Successfully tested retrieval using indexed project documents.

Verified:

* Query embeddings are generated successfully
* Cosine distance search executes correctly
* HNSW vector search returns relevant chunks
* Results are ordered by increasing cosine distance
* Configurable Top-K retrieval functions correctly
* Retrieved chunks are semantically relevant to the user's question

---

## Retrieval Pipeline

The completed semantic retrieval pipeline is:

```text
User Question
      ↓
GeminiEmbedder
      ↓
768-D Query Embedding
      ↓
DocumentChunkRepository
      ↓
pgvector Cosine Distance Search
      ↓
Top-K Retrieved Chunks
      ↓
SemanticRetriever
```

---

## Outcome

The project now contains a fully functional semantic retrieval layer capable of finding the most relevant document chunks using vector similarity search.

For every user question:

* A query embedding is generated using the Gemini embedding model.
* PostgreSQL performs cosine distance search using pgvector against the stored document embeddings.
* The HNSW vector index accelerates nearest-neighbour retrieval.
* The retriever returns the most relevant document chunks as `RetrievedChunk` objects, ready to be consumed by the upcoming LangGraph RAG workflow.

This establishes the retrieval foundation required for Retrieval-Augmented Generation (RAG).

---

## Status

**✅ Part 5 Completed**


---------------------------------------------------------------------------------------------------------------------------------------------
---

# Week 7 – Part 6: LangGraph Retriever Node

* **Status:** ✅ Completed
* **Objective:** Integrate the semantic retrieval pipeline into LangGraph by creating a dedicated **RAG (Retriever) Node**. This node is responsible for retrieving the most relevant document chunks for a user's query and storing them in the graph state so that downstream nodes can use the retrieved context.

---

# Goal

The previous parts of Week 7 focused on building the retrieval infrastructure:

* Enabled **pgvector** for vector similarity search.
* Created the **DocumentChunk** model and HNSW index.
* Implemented **GeminiEmbedder** for generating vector embeddings.
* Built **DocumentChunker** for splitting documents into semantic chunks.
* Implemented **SemanticRetriever** to perform embedding generation and vector search.

In this part, these components were integrated into the **LangGraph workflow** by introducing a dedicated Retriever Node.

---

# Architecture Before Part 6

Initially, the LangGraph execution flow consisted of only a chatbot node.

```text
START
   │
   ▼
Chatbot Node
   │
   ▼
END
```

The chatbot generated responses directly without retrieving any contextual information from the knowledge base.

---

# Architecture After Part 6

The graph now performs document retrieval before generating a response.

```text
START
   │
   ▼
RAG Retriever Node
   │
   ▼
Chatbot Node
   │
   ▼
END
```

This establishes the foundation of a Retrieval-Augmented Generation (RAG) pipeline.

---

# Components Implemented

## 1. RAG Node Factory

Created:

```text
backend/app/graph/nodes/rag.py
```

Instead of directly creating a node, a factory function was implemented.

```python
create_rag_node(db: Session)
```

The factory receives a SQLAlchemy database session and creates all dependencies only once.

Dependencies created:

* DocumentChunkRepository
* GeminiEmbedder
* SemanticRetriever

Finally, it returns the actual LangGraph node.

This approach follows dependency injection principles and avoids creating expensive objects every time the graph executes.

---

## 2. Dependency Injection

The RAG node receives its dependencies through the factory.

```text
Database Session
        │
        ▼
DocumentChunkRepository
        │
        ▼
SemanticRetriever
        │
        ▼
RAG Node
```

The LangGraph state remains independent of database connections.

The graph state contains only business data, while infrastructure objects remain outside the state.

---

## 3. Query Extraction

The RAG node reads the user's question from the graph state.

```python
query = state["query"]
```

The graph state now carries the user query between nodes.

---

## 4. Semantic Retrieval

The node delegates retrieval to the SemanticRetriever.

```python
retrieved_docs = retriever.retrieve(
    question=query,
    top_k=5,
)
```

Internally, the retriever performs:

1. Generate an embedding for the user query.
2. Perform vector similarity search using pgvector.
3. Retrieve the top 5 most relevant document chunks.
4. Return the results as `RetrievedChunk` objects.

The RAG node does not contain embedding logic or SQL queries, maintaining a clean separation of responsibilities.

---

## 5. Updating the Graph State

The node returns only the retrieved documents.

```python
return {
    "retrieved_docs": retrieved_docs,
}
```

LangGraph automatically merges this partial update into the existing graph state.

The RAG node does not modify:

* query
* messages
* response

It only enriches the graph state with retrieval results.

---

# Graph State

The graph state now contains an additional field.

```python
retrieved_docs: list[RetrievedChunk]
```

The state flows through the graph as follows.

Before retrieval:

```text
query
messages
retrieved_docs = []
response
```

After retrieval:

```text
query
messages
retrieved_docs = [RetrievedChunk, RetrievedChunk, ...]
response
```

The chatbot node now receives both the original query and the retrieved context.

---

# Retrieval Flow

The complete retrieval pipeline executed by the RAG node is:

```text
User Query
      │
      ▼
RAG Node
      │
      ▼
SemanticRetriever
      │
      ▼
GeminiEmbedder
      │
      ▼
768-dimensional Query Embedding
      │
      ▼
pgvector Similarity Search
      │
      ▼
Top-k Document Chunks
      │
      ▼
Graph State (retrieved_docs)
```

Each component has a single responsibility.

* GeminiEmbedder → Generates embeddings.
* DocumentChunkRepository → Executes vector search.
* SemanticRetriever → Coordinates retrieval.
* RAG Node → Orchestrates retrieval within LangGraph.

---

# Integration with LangGraph

The graph was updated to register the new node.

```text
START
   │
   ▼
RAG
   │
   ▼
Chatbot
   │
   ▼
END
```

The RAG node executes first, ensuring that document retrieval completes before the chatbot begins generating a response.

---

# Standalone Testing

A standalone test file was created.

```text
backend/test_rag_node.py
```

The test manually invokes the RAG node without running FastAPI or the full LangGraph workflow.

Test process:

```text
Create Database Session
        │
        ▼
Create RAG Node
        │
        ▼
Create Fake ChatState
        │
        ▼
Execute RAG Node
        │
        ▼
Retrieve Top-k Chunks
        │
        ▼
Print Retrieved Documents
        │
        ▼
Verify Results
```

The following conditions were verified:

* The query remains unchanged.
* The retriever successfully returns relevant document chunks.
* The node returns the expected graph state update.
* The retrieved documents are ordered by cosine similarity.

This confirmed that the retrieval pipeline works independently before integrating it into the complete application.

---

# Design Decisions

Several important architectural decisions were made during implementation.

### Dependency Injection

Dependencies are created once inside the factory rather than during every graph execution.

This improves performance and keeps the node lightweight.

---

### Separation of Responsibilities

Each component performs one specific task.

* RAG Node → Graph orchestration.
* SemanticRetriever → Retrieval workflow.
* GeminiEmbedder → Embedding generation.
* Repository → Database operations.

This modular design improves maintainability and makes individual components easier to test.

---

### Partial State Updates

Instead of returning the complete graph state, the node returns only the updated field.

```python
return {
    "retrieved_docs": retrieved_docs,
}
```

LangGraph merges the returned dictionary into the existing state automatically.

This follows LangGraph's recommended design pattern and keeps nodes independent.

---

# Final Workflow

The retrieval workflow implemented in Part 6 is:

```text
User submits a query
        │
        ▼
LangGraph starts execution
        │
        ▼
RAG Node receives ChatState
        │
        ▼
Extract query from state
        │
        ▼
Generate query embedding
        │
        ▼
Perform pgvector similarity search
        │
        ▼
Retrieve top 5 document chunks
        │
        ▼
Store retrieved chunks in graph state
        │
        ▼
Pass enriched state to Chatbot Node
        │
        ▼
Continue graph execution
```

---

# Outcome

By the end of Week 7 – Part 6, the LangGraph workflow was successfully extended with a dedicated Retriever Node. The graph now performs semantic retrieval before response generation, enabling retrieval-augmented workflows. The implementation follows clean architecture principles through dependency injection, separation of concerns, and partial state updates, establishing the foundation for future enhancements where the chatbot will use the retrieved context to generate grounded responses.
