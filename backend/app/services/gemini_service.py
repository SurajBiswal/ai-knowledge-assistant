from app.core.config import settings
import google.generativeai as genai

# Configure the Gemini API key for the generative AI service
genai.configure(api_key=settings.GEMINI_API_KEY)

# Initialize the Gemini generative model for text generation
model = genai.GenerativeModel("gemini-2.5-flash")

# This function takes a prompt string, sends it to the Gemini AI model, and returns the generated response text.
def generate_response(prompt: str) -> str:
    response = model.generate_content(prompt)
    return response.text

def generate_stream_response(prompt: str):
    # This function demonstrates how to generate a streaming response from the Gemini model.
    # It yields chunks of text as they are generated, which can be used for real-time streaming in the frontend.
    stream = model.generate_content(prompt, stream=True)

    for chunk in stream:
        yield chunk.text