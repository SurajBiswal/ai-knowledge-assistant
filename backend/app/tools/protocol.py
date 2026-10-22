"""Small Pydantic message models for generic tool calls and results.

These types document the boundary between model-requested arguments and
application-produced results. The active LangGraph state uses closely related
TypedDict structures in ``app.graph.state``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolCall(BaseModel):
    """Provider-neutral representation of an LLM-requested tool call."""

    model_config = ConfigDict(extra="forbid")

    tool: str = Field(min_length=1)  # Registry name requested by the model.
    arguments: dict[str, Any] = Field(default_factory=dict)  # Tool input values.


class ToolResult(BaseModel):
    """Provider-neutral structured result returned by application code."""

    model_config = ConfigDict(extra="forbid")

    tool: str = Field(min_length=1)  # Tool that was executed.
    result: dict[str, Any] = Field(default_factory=dict)  # Structured output.
    error: str | None = None  # Safe failure text when execution did not succeed.


class ToolMessage(BaseModel):
    """Conceptual message sent back to the model after tool execution."""

    model_config = ConfigDict(extra="forbid")

    tool: str = Field(min_length=1)
    result: dict[str, Any] = Field(default_factory=dict)


def normalize_tool_call(name: str, arguments: dict[str, Any] | None) -> ToolCall:
    """Convert a provider call name/arguments into the shared ToolCall model."""
    return ToolCall(tool=name, arguments=arguments or {})
