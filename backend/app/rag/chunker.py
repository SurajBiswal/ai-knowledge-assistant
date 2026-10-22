"""Split extracted document text into overlapping searchable chunks.

RAGService uses ``DocumentChunker`` during indexing. The returned ``Chunk``
objects preserve order and character positions, which are later stored as
DocumentChunk records and can support source information.
"""

from operator import index

from langchain_text_splitters import RecursiveCharacterTextSplitter
from dataclasses import dataclass
from typing import List, Any

@dataclass(slots=True)
class Chunk:
    """One temporary text section produced before it is saved to the database."""

    # Position of this section in the original document.
    chunk_index: int
    # Text that will be embedded and stored for retrieval.
    chunk_text: str
    # Character start/end details passed into the stored chunk metadata.
    metadata: dict[str, Any]


class DocumentChunker:
    """Create overlapping chunks so relevant text is not cut at hard boundaries."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """Configure chunk length and overlap for the text splitter."""
        # Overlap repeats some text between neighboring chunks for context.
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk_text(
        self,
        text: str,
    )-> List[Chunk]:
        """Split non-empty text and return ordered chunks with character ranges."""
        
        if not text.strip():
            return []
        
        split_chunks = self.text_splitter.split_text(text)

        chunks: list[Chunk] = []

        # current_position = 0
        search_start = 0

        for index, chunk_text in enumerate(split_chunks):
            # char_start = current_position
            # char_end = current_position + len(chunk_text)
            char_start = text.find(chunk_text, search_start)

            if char_start == -1:
                raise ValueError(
                    f"Unable to locate chunk {index} in the original text."
                )

            char_end = char_start + len(chunk_text)            

            chunks.append(
                Chunk(
                    chunk_index=index,
                    chunk_text=chunk_text,
                    metadata={
                        "char_start": char_start,
                        "char_end": char_end,
                    },
                )
            )

            # current_position = char_end - self.chunk_overlap
            search_start = max(0, char_end - self.chunk_overlap)

        return chunks
