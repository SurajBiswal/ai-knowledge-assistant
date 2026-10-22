"""Legacy grounded-answer node from the earlier direct Gemini RAG graph.

It turns existing RAG context into a prompt and calls the application-level
Gemini helper. The active graph does not register this node; current chat uses
the provider-neutral Agent and Tool Nodes instead.
"""

import app.graph.state as chatState

from app.rag.prompt_builder import PromptBuilder
from app.services.gemini_service import generate_response


# Shared deterministic prompt formatter used when this legacy node is called.
prompt_builder = PromptBuilder()


def chatbot_node(state: chatState):
    """Build a grounded prompt from legacy state and return Gemini's answer."""

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
