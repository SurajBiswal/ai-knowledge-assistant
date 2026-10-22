from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.graph.graph import create_graph
from app.llm.base import (
    ConversationMessage,
    ModelResponse,
    ToolCall,
    ToolCallingLLM,
)
from app.mcp.adapters.tool_adapter import MCPToolAdapter
from app.tools.registry import ToolRegistry


# This lightweight content block has the MCP SDK class name expected by the
# adapter, letting the test exercise normalization without a real MCP process.
class TextContent:
    # This initializer stores the text returned by the dummy remote tool.
    def __init__(self, text: str) -> None:
        self.text = text


# This in-process manager implements the adapter's call contract and records
# invocations, so the test proves an asynchronous MCP call actually occurred.
class DummyMCPClientManager:
    # This initializer creates an invocation log used by the final assertions.
    def __init__(self) -> None:
        self.calls: list[dict] = []

    # This async method behaves like a remote echo MCP tool while avoiding any
    # transport, credentials, or third-party server dependency in the test.
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict,
    ):
        self.calls.append(
            {
                "server_name": server_name,
                "tool_name": tool_name,
                "arguments": arguments,
            }
        )
        echoed_text = str(arguments["text"])
        return SimpleNamespace(
            is_error=False,
            structured_content={"echo": echoed_text},
            content=[TextContent(f"Echo: {echoed_text}")],
        )


# This deterministic LLM first requests the dummy MCP tool and then turns the
# returned tool payload into a final response, reproducing the full agent loop.
class DummyToolCallingLLM(ToolCallingLLM):
    # This initializer tracks generation turns and whether cleanup occurred.
    def __init__(self) -> None:
        self.generate_calls = 0
        self.closed = False

    # This method returns a tool call on turn one and a final answer on turn two.
    def generate(self, conversation, tools):
        self.generate_calls += 1

        if self.generate_calls == 1:
            assert [tool.name for tool in tools] == ["mcp_dummy_echo"]
            response = ModelResponse(
                tool_calls=(
                    ToolCall(
                        name="mcp_dummy_echo",
                        arguments={"text": "hello from LangGraph"},
                        call_id="dummy_call_1",
                    ),
                )
            )
        else:
            tool_result = conversation.messages[-1].tool_results[0]
            echoed_text = tool_result.result["structured_content"]["echo"]
            response = ModelResponse(text=f"Dummy MCP returned: {echoed_text}")

        conversation.messages.append(
            ConversationMessage(
                role="assistant",
                text=response.text,
                tool_calls=response.tool_calls,
            )
        )
        return response

    # This cleanup hook proves the agent closes its selected client at the end.
    def close(self) -> None:
        self.closed = True


# This test registers one adapted dummy MCP tool and executes the compiled
# LangGraph end to end through agent, async Tool Node, and final agent response.
def test_langgraph_executes_a_dummy_mcp_tool_end_to_end() -> None:
    user_id = uuid4()
    manager = DummyMCPClientManager()
    llm = DummyToolCallingLLM()

    # This factory supplies the same dummy MCP registration to both graph nodes.
    def create_dummy_registry(**_) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(
            MCPToolAdapter(
                manager=manager,
                server_name="dummy",
                remote_tool_name="echo",
                description="Echo text through a dummy asynchronous MCP tool.",
                input_schema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            )
        )
        return registry

    llm_factory = SimpleNamespace(create_for_user=Mock(return_value=llm))
    graph = create_graph(
        db=Mock(),
        tool_registry_factory=create_dummy_registry,
        llm_provider_factory=lambda **_: llm_factory,
    )

    result = asyncio.run(
        graph.ainvoke(
            {
                "user_id": str(user_id),
                "conversation_id": str(uuid4()),
                "query": "Use the dummy MCP echo tool.",
                "messages": [],
            }
        )
    )

    assert result["response"] == "Dummy MCP returned: hello from LangGraph"
    assert result["sources"] == []
    assert manager.calls == [
        {
            "server_name": "dummy",
            "tool_name": "echo",
            "arguments": {"text": "hello from LangGraph"},
        }
    ]
    llm_factory.create_for_user.assert_called_once_with(user_id=user_id)
    assert llm.generate_calls == 2
    assert llm.closed is True
