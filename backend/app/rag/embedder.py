from google import genai

from app.core.config import settings


class GeminiEmbedder:

    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

    def generate_embedding(
        self,
        text: str,
    ) -> list[float]:

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