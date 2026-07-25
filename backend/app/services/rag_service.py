from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.repositories.document_repository import DocumentRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.rag.chunker import DocumentChunker
from app.rag.embedder import GeminiEmbedder
from app.rag.extractor import DocumentExtractor
from app.rag.retriever import SemanticRetriever, RetrievedChunk

class RAGService:

    def __init__(
        self,
        document_repository: DocumentRepository,
        chunk_repository: DocumentChunkRepository,
        retriever: SemanticRetriever,
    )->None:
        self.document_repository = document_repository
        self.chunk_repository = chunk_repository
        self.extractor = DocumentExtractor()
        self.chunker = DocumentChunker()
        self.embedder = GeminiEmbedder()
        self.retriever = retriever


    def index_document(self, document: Document)-> None:
            """
                Process an uploaded document by extracting its text,
                splitting it into chunks, generating embeddings,
                and storing the chunks for semantic retrieval.
            """

            # Step 1: Extracting text from the document (PDF, DOCX, TXT)
            text = self.extractor.extract(document.file_path, document.file_type)

            # Step 2 — Chunking
            chunks = self.chunker.chunk_text(text)

            # Step 3 — Embeddings
            for chunk in chunks:
                embedding = self.embedder.generate_embedding(
                    chunk.chunk_text
                )
                document_chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.chunk_text,
                    embedding=embedding,
                    chunk_metadata=chunk.metadata
                )
                self.chunk_repository.create(document_chunk)
            document.status = "processed"
            self.document_repository.update(document)

    def retrieve(
    self,
    question: str,
    top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """
        Retrieve the most relevant document chunks for a user question.

        This method delegates semantic search to the SemanticRetriever,
        which generates the query embedding and performs vector similarity
        search against the indexed document chunks.

        Args:
            question: User's natural language query.
            top_k: Maximum number of chunks to retrieve.

        Returns:
            A list of retrieved document chunks ordered by semantic similarity.
        """
        return self.retriever.retrieve(
            question=question,
            top_k=top_k,
        )