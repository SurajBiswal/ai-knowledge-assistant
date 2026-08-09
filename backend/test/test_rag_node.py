from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL
from app.graph.nodes.rag import create_rag_node


# Create SQLAlchemy session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

db = SessionLocal()


try:
    # Create the RAG node
    rag_node = create_rag_node(db)

    # Fake AgentState
    state = {
        "conversation_id": "test-conversation",
        "query": "What is Gemini embedding?",
        "messages": [],
        "retrieved_docs": [],
        "response": "",
    }

    print("=" * 60)
    print("Before Retrieval")
    print("=" * 60)
    print(state)

    # Invoke the node
    updated_state = rag_node(state)

    print("\n" + "=" * 60)
    print("After Retrieval")
    print("=" * 60)
    print(updated_state)

    print("\n" + "=" * 60)
    print("Retrieved Documents")
    print("=" * 60)

    for i, chunk in enumerate(updated_state["retrieved_docs"], start=1):
        print(f"\nChunk {i}")
        print(f"Document ID     : {chunk.document_id}")
        print(f"Chunk Index     : {chunk.chunk_index}")
        print(f"Cosine Distance : {chunk.cosine_distance}")
        print(f"Metadata        : {chunk.metadata}")
        print(f"Text            :")
        print(chunk.chunk_text)

    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    print(
        "Query unchanged:",
        state["query"] == "What is Gemini embedding?"
    )

    print(
        "Retrieved docs populated:",
        len(updated_state["retrieved_docs"]) > 0
    )

finally:
    db.close()