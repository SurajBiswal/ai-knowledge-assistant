from uuid import UUID

from app.graph.graph import graph
from app.repositories.conversation_repository import (
    ConversationRepository,
)
from app.repositories.message_repository import (
    MessageRepository,
)


class ChatService:

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
    ):
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository

    def create_conversation(
        self,
        user_id: UUID,
        title: str,
        mode: str = "chat",
    ):
        return self.conversation_repository.create(
            user_id=user_id,
            title=title,
            mode=mode,
        )

    def get_conversation(
        self,
        conversation_id: UUID,
    ):
        return self.conversation_repository.get_by_id(
            conversation_id
        )

    def list_conversations(
        self,
        user_id: UUID,
    ):
        return self.conversation_repository.list_by_user(
            user_id
        )

    def delete_conversation(
        self,
        conversation_id: UUID,
    ):
        return self.conversation_repository.delete(
            conversation_id
        )

    def get_messages(
        self,
        conversation_id: UUID,
    ):
        return self.message_repository.list_by_conversation(
            conversation_id
        )

# This method handles sending a user message to the AI model, saving both the user and assistant messages to the database, and returning the assistant's response.
    def send_message(
        self,
        conversation_id: UUID,
        user_message: str,
    ):
        # Fetch the conversation from DB
        conversation = self.get_conversation(
            conversation_id
        )

        if not conversation:
            raise ValueError(
                "Conversation not found"
            )

        # Load previous history BEFORE saving
        history = (
            self.message_repository.get_last_n_messages(
                conversation_id=conversation_id,
                limit=10,
            )
        )

        # Save user message to DB immediately 
        self.message_repository.create(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )

        # Convert database messages into format for AI graph
        graph_messages = [
            {
                "role": msg.role,
                "content": msg.content,
            }
            for msg in history
        ]


        try:
            # INVOKE THE LANGGRAPH (AI Pipeline)
            result = graph.invoke(
                {
                    "conversation_id": str(conversation_id),
                    "message": user_message,
                    "messages": graph_messages,
                }
            )
        except Exception as e:
            raise RuntimeError(
                f"Graph execution failed: {str(e)}"
            )

        # Extract AI response
        assistant_response = result["response"]

        # Save ASSISTANT's message to database
        assistant_message = (
            self.message_repository.create(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_response,
            )
        )

        return assistant_message