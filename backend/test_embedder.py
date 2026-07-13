from app.rag.embedder import GeminiEmbedder

embedder = GeminiEmbedder()

vector = embedder.generate_embedding(
    "Artificial Intelligence is transforming software development."
)

print(len(vector))
print(vector[:10])