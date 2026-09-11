from __future__ import annotations

from typing import Literal

from app.graph.state import ChatState


def should_use_tool(
    state: ChatState,
) -> Literal["tools", "end"]:
    """
    Decide the next LangGraph branch.

    The LLM decides whether a tool is required.

    This router only reads the structured decision
    already stored in state.

    Flow:

        Agent
          ↓
      tool_calls?
        │
        ├── yes → Tool Node
        │
        └── no  → END
    """

    tool_calls = state.get(
        "tool_calls",
        [],
    )

    if tool_calls:
        return "tools"

    return "end"