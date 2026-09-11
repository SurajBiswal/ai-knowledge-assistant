from unittest.mock import Mock
from uuid import UUID

from app.tools.workspace_stats import WorkspaceStatsTool


USER_ID = UUID("82ff9f42-6ee7-4379-9227-f12f9805adc9")


def build_tool():
    document_repository = Mock()
    chunk_repository = Mock()
    conversation_repository = Mock()
    message_repository = Mock()

    document_repository.count_by_user.return_value = 12
    chunk_repository.count_by_user.return_value = 1847
    conversation_repository.count_by_user.return_value = 34
    message_repository.count_by_user.return_value = 421

    tool = WorkspaceStatsTool(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        user_id=USER_ID,
    )

    return (
        tool,
        document_repository,
        chunk_repository,
        conversation_repository,
        message_repository,
    )


def test_workspace_stats_returns_user_scoped_counts():
    (
        tool,
        document_repository,
        chunk_repository,
        conversation_repository,
        message_repository,
    ) = build_tool()

    result = tool.execute({})

    assert result.model_dump() == {
        "documents": 12,
        "chunks": 1847,
        "conversations": 34,
        "messages": 421,
    }

    document_repository.count_by_user.assert_called_once_with(USER_ID)
    chunk_repository.count_by_user.assert_called_once_with(USER_ID)
    conversation_repository.count_by_user.assert_called_once_with(USER_ID)
    message_repository.count_by_user.assert_called_once_with(USER_ID)


def test_workspace_stats_does_not_accept_user_id_from_llm():
    tool, *_ = build_tool()

    try:
        tool.execute({"user_id": str(UUID("00000000-0000-0000-0000-000000000001"))})
    except Exception:
        pass
    else:
        raise AssertionError("Unexpected user_id should be rejected.")
