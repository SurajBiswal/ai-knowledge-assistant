from uuid import UUID

from fastapi import HTTPException

from app.graph.graph import create_graph
from app.repositories.conversation_repository import (
    ConversationRepository,
)
from app.repositories.message_repository import (
    MessageRepository,
)
# STREAMING: Import the streaming response function from Gemini service
from app.services.gemini_service import (
    generate_stream_response,
    generate_conversation_title,
)


class ChatService:

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
    ):
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository
        self.db = conversation_repository.db

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

    def rename_conversation(
        self,
        user,
        conversation_id: UUID,
        title: str,
    ):
        conversation = self.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        if conversation.user_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized",
            )

        renamed = self.conversation_repository.rename(
            conversation_id=conversation_id,
            title=title,
        )

        if not renamed:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        return renamed

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
        
        # If this is still a new chat, I should generate a title before continuing.
        if conversation.title == "New Chat":
            try:
                generated_title = generate_conversation_title(
                    user_message
                )

                self.conversation_repository.rename(
                    conversation_id=conversation_id,
                    title=generated_title,
                )
            except Exception:
                pass

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
            graph = create_graph(self.db)
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

    # STREAMING: New method that yields AI response chunks in real-time
    # This allows frontend to display text gradually as it's being generated
    def send_message_stream(
        self,
        conversation_id: UUID,
        user_message: str,
    ):
        # STREAMING: Fetch the conversation from DB
        conversation = self.get_conversation(
            conversation_id
        )

        if not conversation:
            raise ValueError(
                "Conversation not found"
            )
        
        if conversation.title == "New Chat":
            try:
                generated_title = generate_conversation_title(
                    user_message
                )

                self.conversation_repository.rename(
                    conversation_id=conversation_id,
                    title=generated_title,
                )
            except Exception:
                pass

        # STREAMING: Load previous history for context (same as send_message)
        history = (
            self.message_repository.get_last_n_messages(
                conversation_id=conversation_id,
                limit=10,
            )
        )

        # STREAMING: Save user message immediately
        self.message_repository.create(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )

        # STREAMING: Build prompt from history (same logic as chatbot_node)
        prompt = ""
        for msg in history:
            prompt += (
                f"{msg.role}: "
                f"{msg.content}\n"
            )
        prompt += f"user: {user_message}"

        # STREAMING: Use full response to collect chunks
        complete_response = ""
        
        try:
            # STREAMING: Call Gemini with streaming enabled
            for chunk in generate_stream_response(prompt):
                complete_response += chunk
                # STREAMING: Yield chunk immediately (frontend receives it)
                yield chunk
        except Exception as e:
            raise RuntimeError(
                f"Streaming failed: {str(e)}"
            )

        # STREAMING: After streaming completes, save full response to DB
        self.message_repository.create(
            conversation_id=conversation_id,
            role="assistant",
            content=complete_response,
        )