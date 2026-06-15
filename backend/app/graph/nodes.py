import app.graph.state as chatState
from app.services.gemini_service import generate_response



def chatbot_node(state:chatState):
    
    response = generate_response(state["message"])

    return {
        "response": response
    }