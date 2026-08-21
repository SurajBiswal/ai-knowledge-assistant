from app.models.document import Document
from app.models.document_chunk import DocumentChunk

from app.repositories.document_repository import (
    DocumentRepository,
)

from app.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)

from app.rag.chunker import DocumentChunker
from app.rag.embedder import GeminiEmbedder
from app.rag.extractor import DocumentExtractor

from app.rag.retriever import RetrievedChunk

from app.rag.context_builder import ContextBuilder

from app.rag.hybrid_retriever import HybridRetriever

from app.rag.cross_encoder_reranker import (
    CrossEncoderReranker,
)


class RAGService:
    """
    Coordinates the document indexing and retrieval pipeline.

    Retrieval pipeline:

        User Question
              |
              v
        HybridRetriever
              |
              v
        Candidate Chunks
              |
              v
        CrossEncoderReranker
              |
              v
        Reranked Chunks
              |
              v
        ContextBuilder
              |
              v
        Grounded Context
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        chunk_repository: DocumentChunkRepository,
        retriever: HybridRetriever,
        reranker: CrossEncoderReranker,
    ) -> None:

        self.document_repository = document_repository
        self.chunk_repository = chunk_repository

        # ---------------------------------------------------------
        # Document processing dependencies
        # ---------------------------------------------------------

        self.extractor = DocumentExtractor()
        self.chunker = DocumentChunker()
        self.embedder = GeminiEmbedder()

        # ---------------------------------------------------------
        # Retrieval pipeline
        # ---------------------------------------------------------

        self.retriever = retriever
        self.reranker = reranker

        # ---------------------------------------------------------
        # Context construction
        # ---------------------------------------------------------

        self.context_builder = ContextBuilder()

    # =============================================================
    # DOCUMENT INDEXING
    # =============================================================

    def index_document(
        self,
        document: Document,
    ) -> None:
        """
        Process an uploaded document.

        Pipeline:

            Document
                |
                v
            Extract text
                |
                v
            Chunk text
                |
                v
            Generate embeddings
                |
                v
            Save DocumentChunk records
        """

        # ---------------------------------------------------------
        # Step 1 — Extract text
        # ---------------------------------------------------------

        text = self.extractor.extract(
            document.file_path,
            document.file_type,
        )

        # ---------------------------------------------------------
        # Step 2 — Chunk document
        # ---------------------------------------------------------

        chunks = self.chunker.chunk_text(text)

        # ---------------------------------------------------------
        # Step 3 — Generate embeddings and save chunks
        # ---------------------------------------------------------

        for chunk in chunks:

            embedding = self.embedder.generate_embedding(
                chunk.chunk_text
            )

            metadata = {
                "document_id": str(document.id),
                "filename": document.filename,
                "page": None,
                "char_start": chunk.metadata.get(
                    "char_start"
                ),
                "char_end": chunk.metadata.get(
                    "char_end"
                ),
            }

            document_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.chunk_text,
                embedding=embedding,
                chunk_metadata=metadata,
            )

            self.chunk_repository.create(
                document_chunk
            )

        # ---------------------------------------------------------
        # Step 4 — Mark document as processed
        # ---------------------------------------------------------

        document.status = "processed"

        self.document_repository.update(
            document
        )

    # =============================================================
    # RETRIEVAL
    # =============================================================

    def retrieve(
    self,
    question: str,
    top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """
        Retrieve and rerank document chunks.

        Pipeline:

            Question
                ↓
            HybridRetriever
                ↓
            Candidate Chunks
                ↓
            CrossEncoderReranker
                ↓
            Final Ranked Chunks
        """

        if top_k <= 0:
            return []

        # Retrieve more candidates than the final number.
        # The reranker needs a larger candidate pool to choose
        # the most relevant chunks.
        candidate_k = max(top_k * 4, 20)

        candidate_chunks = self.retriever.retrieve(
            question=question,
            top_k=candidate_k,
        )

        if not candidate_chunks:
            return []

        # Rerank candidates using the Cross Encoder.
        reranked_chunks = self.reranker.rerank(
            question=question,
            retrieved_chunks=candidate_chunks,
            top_k=top_k,
        )

        return reranked_chunks


    # =============================================================
    # RETRIEVE + BUILD CONTEXT
    # =============================================================

    def retrieve_context(
        self,
        question: str,
        top_k: int = 5,
    ) -> str:
        """
        Retrieve reranked chunks and build prompt-ready context.

        Pipeline:

            Question
                |
                v
            HybridRetriever
                |
                v
            Candidate Chunks
                |
                v
            CrossEncoderReranker
                |
                v
            Reranked Chunks
                |
                v
            ContextBuilder
                |
                v
            Context String
        """

        # ---------------------------------------------------------
        # Step 1 — Retrieve + rerank
        # ---------------------------------------------------------

        retrieved_chunks = self.retrieve(
            question=question,
            top_k=top_k,
        )

        # ---------------------------------------------------------
        # Step 2 — Build context
        # ---------------------------------------------------------

        return self.build_context(
            retrieved_chunks
        )

    # =============================================================
    # BUILD CONTEXT
    # =============================================================

    def build_context(
        self,
        retrieved_chunks: list[RetrievedChunk],
    ) -> str:
        """
        Build a structured context string from retrieved chunks.

        This method only performs context construction.

        It does NOT:

        - retrieve documents
        - generate embeddings
        - rerank documents
        - rewrite queries
        """

        return self.context_builder.build_context(
            retrieved_chunks
        )