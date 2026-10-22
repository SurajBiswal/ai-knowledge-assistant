"""Conversation storage and LangGraph chat orchestration.

Conversation API routes call this service. It checks for an active user-owned
LLM profile, stores messages through repositories, invokes the asynchronous
LangGraph agent/tool loop, and saves the final assistant response.
"""

from uuid import UUID

from fastapi import HTTPException

from app.graph.graph import create_graph
from app.llm.factory import LLMProviderFactory
from app.repositories.conversation_repository import (
    ConversationRepository,
)
from app.repositories.message_repository import (
    MessageRepository,
)
# The legacy Gemini helper is used only to generate a short conversation title.
from app.services.gemini_service import (
    generate_conversation_title,
)


class ChatService:
    """Join conversation persistence with user-specific LLM/tool execution."""

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
    ):
        """Store both repositories and their shared request database session."""
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository
        self.db = conversation_repository.db

    def create_conversation(
        self,
        user_id: UUID,
        title: str,
        mode: str = "chat",
    ):
        """Create and return a conversation owned by ``user_id``."""
        return self.conversation_repository.create(
            user_id=user_id,
            title=title,
            mode=mode,
        )

    def get_conversation(
        self,
        conversation_id: UUID,
    ):
        """Return a conversation by ID, or None when it does not exist."""
        return self.conversation_repository.get_by_id(
            conversation_id
        )

    def rename_conversation(
        self,
        user,
        conversation_id: UUID,
        title: str,
    ):
        """Verify ownership, rename the conversation, and return it."""
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
        """Return conversations belonging to one authenticated user."""
        return self.conversation_repository.list_by_user(
            user_id
        )

    def delete_conversation(
        self,
        conversation_id: UUID,
    ):
        """Delete a conversation by ID and return whether it existed."""
        return self.conversation_repository.delete(
            conversation_id
        )

    def get_messages(
        self,
        conversation_id: UUID,
    ):
        """Return all stored messages for one conversation."""
        return self.message_repository.list_by_conversation(
            conversation_id
        )

    def require_configured_llm(self, *, user_id: UUID) -> None:
        """Stop chat early when the user has no tested active LLM profile."""
        LLMProviderFactory(db=self.db).require_active_profile(user_id=user_id)

    # This method awaits the graph so its asynchronous MCP Tool Node can run,
    # then saves the completed message using the existing repositories.
    async def send_message(
        self,
        conversation_id: UUID,
        user_message: str,
    ):
        """Run one complete graph turn, save the answer, and return its Message."""
        # Fetch the conversation from DB
        conversation = self.get_conversation(
            conversation_id
        )

        if not conversation:
            raise ValueError(
                "Conversation not found"
            )

        self.require_configured_llm(user_id=conversation.user_id)

        # Generate title for a new conversation
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

        # Load previous history
        history = (
            self.message_repository.get_last_n_messages(
                conversation_id=conversation_id,
                limit=10,
            )
        )

        # Save user message
        self.message_repository.create(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )

        # Convert history for LangGraph
        graph_messages = [
            {
                "role": msg.role,
                "content": msg.content,
            }
            for msg in history
        ]

        try:
            graph = create_graph(self.db)

            result = await graph.ainvoke(
                {
                    "user_id": str(conversation.user_id),
                    "conversation_id": str(conversation_id),
                    "query": user_message,
                    "messages": graph_messages,
                }
            )

        except Exception as e:
            raise RuntimeError(
                f"Graph execution failed: {str(e)}"
            )

        assistant_response = result["response"]

        sources = result.get("sources", [])

        assistant_message = (
            self.message_repository.create(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_response,
                sources=sources,
            )
        )

        return assistant_message

    # This async generator waits for the tool-capable graph and remains directly
    # consumable by FastAPI's StreamingResponse without blocking MCP execution.
    async def send_message_stream(
        self,
        conversation_id: UUID,
        user_message: str,
    ):
        """Run one graph turn and yield its completed answer as one text chunk."""

        # ---------------------------------------------------------
        # Fetch conversation
        # ---------------------------------------------------------

        conversation = self.get_conversation(
            conversation_id
        )

        if not conversation:
            raise ValueError(
                "Conversation not found"
            )

        self.require_configured_llm(user_id=conversation.user_id)

        # ---------------------------------------------------------
        # Generate title for a new conversation
        # ---------------------------------------------------------

        if conversation.title == "New Chat":
            try:
                generated_title = (
                    generate_conversation_title(
                        user_message
                    )
                )

                self.conversation_repository.rename(
                    conversation_id=conversation_id,
                    title=generated_title,
                )

            except Exception:
                pass

        # ---------------------------------------------------------
        # Load previous history
        # ---------------------------------------------------------

        history = (
            self.message_repository
            .get_last_n_messages(
                conversation_id=conversation_id,
                limit=10,
            )
        )

        # ---------------------------------------------------------
        # Save user message
        # ---------------------------------------------------------

        self.message_repository.create(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )

        # ---------------------------------------------------------
        # Convert history for graph state
        # ---------------------------------------------------------

        graph_messages = [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in history
        ]

        # ---------------------------------------------------------
        # Execute Layer 2 graph
        # ---------------------------------------------------------

        try:

            graph = create_graph(
                self.db
            )

            result = await graph.ainvoke(
                {
                    "user_id": str(
                        conversation.user_id
                    ),
                    "conversation_id": str(
                        conversation_id
                    ),
                    "query": user_message,
                    "messages": graph_messages,
                }
            )

            complete_response = result[
                "response"
            ]

            sources = result.get(
                "sources",
                [],
            )

        except Exception as e:
            raise RuntimeError(
                f"Graph execution failed: {str(e)}"
            )

        # ---------------------------------------------------------
        # Current Layer 2 streaming behavior
        #
        # ToolCallingService is synchronous, so yield the completed
        # answer as one chunk.
        # ---------------------------------------------------------

        yield complete_response

        # ---------------------------------------------------------
        # Save assistant response
        # ---------------------------------------------------------

        self.message_repository.create(
            conversation_id=conversation_id,
            role="assistant",
            content=complete_response,
            sources=sources,
        )
