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
