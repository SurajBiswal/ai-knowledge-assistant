from google import genai

from app.core.config import settings


QUERY_REWRITE_PROMPT = """
You are an AI assistant that rewrites user questions into optimized semantic search
queries for a Retrieval-Augmented Generation (RAG) system.

Your goal is to improve document retrieval, not to answer the user's question.

Rules:

- Preserve the user's original intent.
- Do NOT answer the question.
- Do NOT invent facts or add information that is not implied by the user's question.
- Rewrite vague or short questions into clear, descriptive semantic search queries.
- Prefer technical keywords, workflows, architecture, APIs, classes, methods, configuration, and implementation details when appropriate.
- Keep the query focused on retrieving information from the indexed documents.
- If the user's question is already clear and specific, return it unchanged.
- Return ONLY the rewritten query.
- Do NOT include explanations, bullet points, markdown, or quotation marks.

User Question:
{question}
""".strip()


class QueryRewriter:

    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

    def rewrite_query(
    self,
    question: str,
    ) -> str:

        question = question.strip()

        if not question:
            raise ValueError(
                "Question cannot be empty."
            )

        prompt = QUERY_REWRITE_PROMPT.format(
            question=question,
        )

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            rewritten_query = (
                response.text or ""
            ).strip()

            if not rewritten_query:
                return question

            return rewritten_query

        except Exception:
            # Fall back to the original query if rewriting fails
            return question