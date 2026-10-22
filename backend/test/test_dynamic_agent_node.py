from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from pydantic import BaseModel

from app.graph.graph import create_graph
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


# This schema describes the fake native search tool exposed to the test LLM.
class SearchInput(BaseModel):
    query: str


# This registry records calls while implementing the same sync and async paths
# as the production registry used by the graph.
class FakeRegistry:
    def __init__(self) -> None:
        self.tool = SimpleNamespace(
            name="search_documents",
            description="Search private documents.",
            input_schema=SearchInput,
            get_definition=lambda: {
                "name": "search_documents",
                "description": "Search private documents.",
                "input_schema": SearchInput.model_json_schema(),
            },
        )
        self.executions: list[tuple[str, dict]] = []

    def get_all_tools(self):
        return {self.tool.name: self.tool}

    def execute(self, *, name: str, arguments: dict):
        self.executions.append((name, arguments))
        return {
            "results": [
                {
                    "document_id": "doc-1",
                    "document": "mysterious-device.pdf",
                    "page": 7,
                    "chunk_index": 13,
                    "content": "The location is Cairo.",
                    "score": 0.94,
                }
            ]
        }

    # This async entry point lets the graph Tool Node treat the fake native tool
    # exactly as the production registry treats synchronous native tools.
    async def execute_async(self, *, name: str, arguments: dict):
        return self.execute(name=name, arguments=arguments)


# This deterministic LLM makes tests exercise the tool loop without a network.
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


# This test proves one selected client survives the async Tool Node round trip.
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

    first_agent_update = asyncio.run(agent(initial_state))

    assert should_use_tool(first_agent_update) == "tools"
    assert first_agent_update["tool_calls"] == [
        {
            "name": "search_documents",
            "arguments": {"query": "mysterious device"},
            "call_id": "call_1",
        }
    ]
    factory.create_for_user.assert_called_once_with(user_id=user_id)

    tool_update = asyncio.run(
        tool_node({**initial_state, **first_agent_update})
    )
    assert registry.executions == [
        ("search_documents", {"query": "mysterious device"})
    ]
    assert tool_update["tool_results"][0]["call_id"] == "call_1"
    assert tool_update["sources"] == [
        {
            "document_id": "doc-1",
            "filename": "mysterious-device.pdf",
            "page": 7,
            "chunk_index": 13,
            "excerpt": "The location is Cairo.",
        }
    ]

    final_update = asyncio.run(
        agent({**initial_state, **first_agent_update, **tool_update})
    )

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


# This test proves direct model answers still bypass tool execution.
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

    update = asyncio.run(
        agent({"user_id": str(user_id), "query": "Hello"})
    )

    assert should_use_tool(update) == "end"
    assert update["response"] == "Hello. How can I help?"
    assert llm.closed is True


# This test proves the compiled graph retains citations produced by the Tool
# Node after the Agent Node writes the final natural-language response.
def test_graph_preserves_document_sources_in_final_state() -> None:
    user_id = uuid4()
    registry = FakeRegistry()
    llm = FakeToolCallingLLM(
        responses=[
            ModelResponse(
                tool_calls=(
                    ToolCall(
                        name="search_documents",
                        arguments={"query": "mysterious device"},
                        call_id="call_sources",
                    ),
                )
            ),
            ModelResponse(text="The device revealed Cairo."),
        ]
    )
    provider_factory = Mock()
    provider_factory.create_for_user.return_value = llm
    graph = create_graph(
        db=Mock(),
        tool_registry_factory=lambda **_: registry,
        llm_provider_factory=lambda **_: provider_factory,
    )

    result = asyncio.run(
        graph.ainvoke(
            {
                "user_id": str(user_id),
                "conversation_id": str(uuid4()),
                "query": "What did the mysterious device reveal?",
                "messages": [],
            }
        )
    )

    assert result["response"] == "The device revealed Cairo."
    assert result["sources"] == [
        {
            "document_id": "doc-1",
            "filename": "mysterious-device.pdf",
            "page": 7,
            "chunk_index": 13,
            "excerpt": "The location is Cairo.",
        }
    ]
