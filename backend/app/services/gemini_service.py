"""Small Gemini helpers retained for direct generation and chat titles.

The active LangGraph agent obtains its model from ``LLMProviderFactory`` and
does not use this module for normal answers. ChatService still calls
``generate_conversation_title`` when a new conversation receives its first text.
"""

from app.core.config import settings
from google import genai

# Shared legacy client built from the application-level Gemini key.
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Model used only by the helper functions in this module.
MODEL_NAME = "gemini-2.5-flash"

# Send one prompt directly to the legacy Gemini client and return its text.
def generate_response(prompt: str) -> str:
    """Return Gemini's complete text response for ``prompt``."""
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )
    return response.text


def generate_stream_response(prompt: str):
    """Yield Gemini text chunks for the optional stream demonstration route."""
    stream = client.models.generate_content_stream(
        model=MODEL_NAME,
        contents=prompt,
    )

    for chunk in stream:
        yield chunk.text


def generate_conversation_title(
    first_message: str,
) -> str:
    """Generate a short title from the first message, with ``New Chat`` fallback."""
    prompt = f"""
Generate a short conversation title.

Maximum 5 words.

Return only the title.

Message:
{first_message}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    title = response.text.strip()

    # Remove surrounding quotes if present
    title = title.strip('"').strip("'")

    # Fallback
    if not title:
        return "New Chat"

    return title
