"""Generate fixed-size Gemini embeddings for semantic document search.

RAG indexing embeds every document chunk. ``SemanticRetriever`` embeds the
user's query with the same model so PostgreSQL pgvector can compare them.
"""

from google import genai

from app.core.config import settings


class GeminiEmbedder:
    """Wrap Gemini's embedding API and enforce the database vector size."""

    def __init__(self):
        """Create a Gemini client using the application's configured key."""
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

    def generate_embedding(
        self,
        text: str,
    ) -> list[float]:
        """Return a 768-number embedding for text or raise a clear error."""

        try:
            response = self.client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config={
                    "output_dimensionality": 768,
                },
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to generate embedding: {e}"
            ) from e

        embedding = response.embeddings[0].values

        if len(embedding) != 768:
            raise ValueError(
                f"Expected embedding dimension 768, got {len(embedding)}"
            )
        
        # print(type(response))
        # print(response)

        return embedding
