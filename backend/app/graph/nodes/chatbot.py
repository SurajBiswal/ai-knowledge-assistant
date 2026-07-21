import app.graph.state as chatState
from app.services.gemini_service import generate_response


def chatbot_node(state: chatState):

    # Step 1: Build the prompt from conversation history
    prompt = ""

    for msg in state["messages"]:
        prompt += (
            f"{msg['role']}: "
            f"{msg['content']}\n"
        )

    prompt += (
        f"user: {state['query']}"
    )

    # Now prompt looks like:
    # user: Hello
    # assistant: Hi there!
    # user: What is Python?
    
    # Step 2: Send to Gemini AI and get response

    response = generate_response(prompt)

    # Step 3: Return new state with response
    return {
        "response": response
    }