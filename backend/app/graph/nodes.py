import google.generativeai as genai

from app.core.config import settings


# Defer model initialization until first use (don't initialize at import time)
model = None


def _get_model():
    global model
    if model is None:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
    return model


def chatbot_node(state):
    user_message = state["message"]
    
    model_instance = _get_model()
    response = model_instance.generate_content(user_message)

    return {
        "response": response.text
    }