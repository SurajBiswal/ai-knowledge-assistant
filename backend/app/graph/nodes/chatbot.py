import app.graph.state as chatState

from app.rag.prompt_builder import PromptBuilder
from app.services.gemini_service import generate_response


prompt_builder = PromptBuilder()


def chatbot_node(state: chatState):

    # Step 1: Read the current user question
    question = state["query"]

    # Step 2: Read the formatted RAG context
    context = state["context"]

    # Step 3: Build the grounded prompt
    prompt = prompt_builder.build_prompt(
        question=question,
        context=context,
    )

    # Step 4: Generate the AI response
    response = generate_response(prompt)

    # Step 5: Return both prompt and response
    return {
        "prompt": prompt,
        "response": response,
        "sources": state["sources"],
    }