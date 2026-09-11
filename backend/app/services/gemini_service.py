from app.core.config import settings
from google import genai

# Initialize the Gemini client (replaces genai.configure() + GenerativeModel())
client = genai.Client(api_key=settings.GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"

# This function takes a prompt string, sends it to the Gemini AI model, and returns the generated response text.
def generate_response(prompt: str) -> str:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )
    return response.text


def generate_stream_response(prompt: str):
    # This function demonstrates how to generate a streaming response from the Gemini model.
    # It yields chunks of text as they are generated, which can be used for real-time streaming in the frontend.
    stream = client.models.generate_content_stream(
        model=MODEL_NAME,
        contents=prompt,
    )

    for chunk in stream:
        yield chunk.text


def generate_conversation_title(
    first_message: str,
) -> str:
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