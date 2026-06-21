from typing import TypedDict


class ChatState(TypedDict):
    conversation_id: str      # Which conversation this is from
    message: str              # The current user message
    messages: list            # All previous messages (conversation history)
    response: str             # The AI-generated response (gets filled in)