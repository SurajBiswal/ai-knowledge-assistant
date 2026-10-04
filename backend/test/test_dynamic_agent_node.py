from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from pydantic import BaseModel

from app.graph.nodes.agent import create_agent_node
from app.graph.nodes.tools import create_tool_node
from app.graph.routing import should_use_tool
from app.llm.base import (
    ConversationMessage,
    ModelResponse,
    ToolCall,
    ToolCallingConversation,
    ToolCallingLLM,
)


class SearchInput(BaseModel):
    query: str


class FakeRegistry:
    def __init__(self) -> None:
        self.tool = SimpleNamespace(
            name="search_documents",
            description="Search private documents.",
            input_schema=SearchInput,
        )
        self.executions: list[tuple[str, dict]] = []

    def get_all_tools(self):
        return {self.tool.name: self.tool}

    def execute(self, *, name: str, arguments: dict):
        self.executions.append((name, arguments))
        return {"results": [{"content": "The location is Cairo."}]}


class FakeToolCallingLLM(ToolCallingLLM):
    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = responses
        self.generate_calls = 0
        self.closed = False

    def generate(self, conversation, tools):
        self.generate_calls += 1
        response = self.responses.pop(0)
        conversation.messages.append(
            ConversationMessage(
                role="assistant",
                text=response.text,
                tool_calls=response.tool_calls,
            )
        )
        return response

    def close(self) -> None:
        self.closed = True


def test_agent_preserves_one_selected_llm_through_tool_loop() -> None:
    user_id = uuid4()
    llm = FakeToolCallingLLM(
        responses=[
            ModelResponse(
                tool_calls=(
                    ToolCall(
                        name="search_documents",
                        arguments={"query": "mysterious device"},
                        call_id="call_1",
                    ),
                )
            ),
            ModelResponse(text="The device revealed Cairo."),
        ]
    )
    registry = FakeRegistry()
    factory = Mock()
    factory.create_for_user.return_value = llm

    agent = create_agent_node(
        db=Mock(),
        tool_registry_factory=lambda **_: registry,
        llm_provider_factory=lambda **_: factory,
    )
    tool_node = create_tool_node(
        db=Mock(),
        tool_registry_factory=lambda **_: registry,
    )
    initial_state = {
        "user_id": str(user_id),
        "query": "What did the mysterious device reveal?",
    }

    first_agent_update = agent(initial_state)

    assert should_use_tool(first_agent_update) == "tools"
    assert first_agent_update["tool_calls"] == [
        {
            "name": "search_documents",
            "arguments": {"query": "mysterious device"},
            "call_id": "call_1",
        }
    ]
    factory.create_for_user.assert_called_once_with(user_id=user_id)

    tool_update = tool_node({**initial_state, **first_agent_update})
    assert registry.executions == [
        ("search_documents", {"query": "mysterious device"})
    ]
    assert tool_update["tool_results"][0]["call_id"] == "call_1"

    final_update = agent({**initial_state, **first_agent_update, **tool_update})

    assert final_update == {
        "tool_calls": [],
        "response": "The device revealed Cairo.",
    }
    assert llm.generate_calls == 2
    assert factory.create_for_user.call_count == 1
    assert llm.closed is True
    assert [message.role for message in first_agent_update["llm_conversation"].messages] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
    ]


def test_agent_returns_a_direct_answer_without_entering_tool_node() -> None:
    user_id = uuid4()
    llm = FakeToolCallingLLM(
        responses=[ModelResponse(text="Hello. How can I help?")]
    )
    registry = FakeRegistry()
    factory = Mock()
    factory.create_for_user.return_value = llm

    agent = create_agent_node(
        db=Mock(),
        tool_registry_factory=lambda **_: registry,
        llm_provider_factory=lambda **_: factory,
    )

    update = agent({"user_id": str(user_id), "query": "Hello"})

    assert should_use_tool(update) == "end"
    assert update["response"] == "Hello. How can I help?"
    assert llm.closed is True
