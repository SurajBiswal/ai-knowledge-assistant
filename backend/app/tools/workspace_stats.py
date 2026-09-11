from __future__ import annotations

from uuid import UUID

from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.message_repository import MessageRepository
from app.tools.base import BaseTool
from app.tools.schemas import WorkspaceStatsInput, WorkspaceStatsOutput


class WorkspaceStatsTool(
    BaseTool[WorkspaceStatsInput, WorkspaceStatsOutput]
):
    """Read-only tool for statistics belonging to one authenticated user.

    The LLM supplies no user identity and no SQL. The application injects
    the authenticated user's ID, while repository methods execute fixed,
    parameterized COUNT queries against PostgreSQL.
    """

    name = "get_workspace_stats"

    description = (
        "Get read-only statistics for the authenticated user's workspace, "
        "including the number of documents, indexed chunks, conversations, "
        "and messages."
    )

    input_schema = WorkspaceStatsInput
    output_schema = WorkspaceStatsOutput

    def __init__(
        self,
        document_repository: DocumentRepository,
        chunk_repository: DocumentChunkRepository,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        user_id: UUID,
    ) -> None:
        self.document_repository = document_repository
        self.chunk_repository = chunk_repository
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository
        self.user_id = user_id

    def execute(
        self,
        arguments: WorkspaceStatsInput,
    ) -> WorkspaceStatsOutput:
        """Return counts for the authenticated user's workspace."""

        self.validate_input(arguments)

        result = WorkspaceStatsOutput(
            documents=self.document_repository.count_by_user(
                self.user_id
            ),
            chunks=self.chunk_repository.count_by_user(
                self.user_id
            ),
            conversations=self.conversation_repository.count_by_user(
                self.user_id
            ),
            messages=self.message_repository.count_by_user(
                self.user_id
            ),
        )

        return self.validate_output(result)
