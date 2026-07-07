You can add the following to your Week 7 documentation.

---

# Week 7 — RAG Foundation

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
