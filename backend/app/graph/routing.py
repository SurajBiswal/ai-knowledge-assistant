"""Routing decision for the active LangGraph workflow.

The Agent Node has already asked the LLM whether tools are needed. This module
only checks the structured ``tool_calls`` field and chooses Tool Node or END; it
does not make an AI or authorization decision.
"""

from __future__ import annotations

from typing import Literal

from app.graph.state import ChatState


def should_use_tool(
    state: ChatState,
) -> Literal["tools", "end"]:
    """
    Return ``tools`` when calls exist, otherwise return ``end``.

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
