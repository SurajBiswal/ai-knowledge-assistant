"""Verify the application's MCP path against a real stdio child process.

Unlike the manager unit test, this module does not replace the MCP SDK client.
It starts the local echo server with the active virtual environment's Python,
discovers and calls its tool, then exercises the same adapter and compiled
LangGraph loop used by the application. The final checks prove cleanup closes
the SDK client and terminates the child process.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import signal
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.graph.graph import create_graph
from app.llm.base import (
    ConversationMessage,
    ModelResponse,
    ToolCall,
    ToolCallingLLM,
)
from app.mcp.adapters.tool_adapter import MCPToolAdapter
from app.mcp.client.manager import MCPClientManager
from app.mcp.config.server_config import MCPServerConfig
from app.tools.registry import ToolRegistry


# The whole lifecycle has one timeout because MCP 2.x requires its AnyIO stdio
# context to open and close in the same asyncio task. Wrapping individual calls
# with asyncio.wait_for() would create extra tasks and break SDK cleanup.
TEST_TIMEOUT_SECONDS = 30.0
PROCESS_EXIT_TIMEOUT_SECONDS = 3.0


# This deterministic model requests the real echo tool once, then converts the
# normalized MCP text result into the final graph response without any API call.
class EchoToolCallingLLM(ToolCallingLLM):
    """Drive a predictable two-turn tool loop for the integration test."""

    def __init__(self, expected_tool_name: str) -> None:
        """Store the discovered public name and initialize test counters."""
        self.expected_tool_name = expected_tool_name
        self.generate_calls = 0
        self.closed = False

    def generate(self, conversation, tools):
        """Request echo first, then answer using the returned MCP text block."""
        self.generate_calls += 1

        if self.generate_calls == 1:
            assert [tool.name for tool in tools] == [self.expected_tool_name]
            response = ModelResponse(
                tool_calls=(
                    ToolCall(
                        name=self.expected_tool_name,
                        arguments={"text": "hello from LangGraph"},
                        call_id="real_stdio_call_1",
                    ),
                )
            )
        else:
            normalized = conversation.messages[-1].tool_results[0].result
            echoed_text = normalized["content"][0]["text"]
            response = ModelResponse(text=f"Real MCP returned: {echoed_text}")

        conversation.messages.append(
            ConversationMessage(
                role="assistant",
                text=response.text,
                tool_calls=response.tool_calls,
            )
        )
        return response

    def close(self) -> None:
        """Record that the Agent Node released the deterministic model client."""
        self.closed = True


# This check uses signal 0, which asks the operating system whether a PID still
# exists without sending a real signal to that process.
def _process_exists(pid: int) -> bool:
    """Return whether the stdio child process is still present."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


# Process shutdown can take a few event-loop turns after the SDK closes stdio,
# so this helper waits briefly instead of depending on an immediate PID check.
async def _wait_for_process_exit(pid: int) -> bool:
    """Wait a bounded time for ``pid`` to disappear and report the result."""
    deadline = time.monotonic() + PROCESS_EXIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if not _process_exists(pid):
            return True
        await asyncio.sleep(0.05)
    return not _process_exists(pid)


# The real scenario is kept in one coroutine so the outer test can apply an
# additional overall timeout while its finally block still performs cleanup.
async def _exercise_real_stdio_server(tmp_path: Path) -> None:
    """Connect, discover, invoke, run LangGraph, and verify process cleanup."""
    server_script = Path(__file__).parent / "servers" / "echo_server.py"
    pid_file = tmp_path / "echo_server.pid"
    config = MCPServerConfig(
        name="real-stdio",
        transport="stdio",
        command=sys.executable,
        args=(str(server_script),),
        env={"MCP_TEST_PID_FILE": str(pid_file)},
    )
    manager = MCPClientManager([config])
    child_pid: int | None = None

    try:
        connected = await manager.connect("real-stdio")
        assert connected == {
            "server": "real-stdio",
            "status": "connected",
            "tool_count": 1,
        }

        child_pid = int(pid_file.read_text(encoding="utf-8"))
        assert _process_exists(child_pid)

        discovered = await manager.discover_tools("real-stdio")
        assert len(discovered) == 1
        assert discovered[0]["name"] == "echo"
        assert discovered[0]["input_schema"]["type"] == "object"
        assert discovered[0]["input_schema"]["properties"]["text"][
            "type"
        ] == "string"

        direct_result = await manager.call_tool(
            "real-stdio",
            "echo",
            {"text": "hello from manager"},
        )
        assert direct_result.is_error is False
        assert direct_result.content[0].text == "Echo: hello from manager"

        adapter = MCPToolAdapter(
            manager=manager,
            server_name="real-stdio",
            remote_tool_name="echo",
            description=discovered[0]["description"],
            input_schema=discovered[0]["input_schema"],
        )
        registry = ToolRegistry()
        registry.register(adapter)

        # Returning the already-built registry makes Agent and Tool Nodes share
        # the exact adapter backed by the real connected manager.
        def create_real_registry(**_) -> ToolRegistry:
            return registry

        llm = EchoToolCallingLLM(expected_tool_name=adapter.name)
        llm_factory = SimpleNamespace(create_for_user=Mock(return_value=llm))
        graph = create_graph(
            db=Mock(),
            tool_registry_factory=create_real_registry,
            llm_provider_factory=lambda **_: llm_factory,
        )

        graph_result = await graph.ainvoke(
            {
                "user_id": str(uuid4()),
                "conversation_id": str(uuid4()),
                "query": "Use the real MCP echo tool.",
                "messages": [],
            }
        )
        assert graph_result["response"] == (
            "Real MCP returned: Echo: hello from LangGraph"
        )
        assert llm.generate_calls == 2
        assert llm.closed is True
    finally:
        # Cleanup runs directly in the same task that opened the SDK client.
        # A forced signal below is only a safety fallback after the assertion.
        await manager.disconnect_all()
        assert manager.list_servers()[0]["status"] == "disconnected"

        if child_pid is None and pid_file.exists():
            child_pid = int(pid_file.read_text(encoding="utf-8"))

        if child_pid is not None:
            exited = await _wait_for_process_exit(child_pid)
            if not exited and _process_exists(child_pid):
                os.kill(child_pid, signal.SIGTERM)
            assert exited, "MCP stdio child remained alive after disconnect"


# This is an integration test: it launches a real MCP server and uses the real
# SDK transport. One overall timeout bounds the complete same-task lifecycle.
@pytest.mark.asyncio
async def test_real_stdio_mcp_tool_runs_through_langgraph(tmp_path: Path) -> None:
    """Prove real stdio discovery, invocation, graph use, and cleanup."""
    await asyncio.wait_for(
        _exercise_real_stdio_server(tmp_path),
        timeout=TEST_TIMEOUT_SECONDS,
    )
