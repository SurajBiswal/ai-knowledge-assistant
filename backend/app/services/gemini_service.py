from app.core.config import settings
import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


def generate_response(prompt: str) -> str:
    response = model.generate_content(prompt)
    return response.text