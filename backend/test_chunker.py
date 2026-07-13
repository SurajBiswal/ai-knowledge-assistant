from app.rag.chunker import DocumentChunker


def main():

    chunker = DocumentChunker(
        chunk_size=1000,
        chunk_overlap=200,
    )

    # Create a long sample document
    text = """
Artificial Intelligence is transforming software development.
Machine Learning enables computers to learn from data.
Large Language Models are widely used in modern AI applications.
""" * 200

    chunks = chunker.chunk_text(text)

    print("=" * 80)
    print("Chunking Test")
    print("=" * 80)

    print(f"Total Chunks: {len(chunks)}")

    # ---------- Assertions ----------

    assert len(chunks) > 0, "No chunks were generated."

    for index, chunk in enumerate(chunks):

        # chunk order
        assert chunk.chunk_index == index

        # chunk text should not be empty
        assert chunk.chunk_text.strip()

        # metadata must exist
        assert "char_start" in chunk.metadata
        assert "char_end" in chunk.metadata

        # valid character positions
        assert chunk.metadata["char_start"] >= 0
        assert chunk.metadata["char_end"] > chunk.metadata["char_start"]

    print("All assertions passed.\n")

    # ---------- Print first 3 chunks ----------

    for chunk in chunks[:3]:

        print("-" * 80)
        print(f"Index: {chunk.chunk_index}")
        print(f"Metadata: {chunk.metadata}")
        print(f"Length: {len(chunk.chunk_text)}")
        print(f"Text:\n{chunk.chunk_text}\n")


if __name__ == "__main__":
    main()