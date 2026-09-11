from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolCall(BaseModel):
    """Provider-neutral representation of an LLM-requested tool call."""

    model_config = ConfigDict(extra="forbid")

    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Provider-neutral structured result returned by application code."""

    model_config = ConfigDict(extra="forbid")

    tool: str = Field(min_length=1)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ToolMessage(BaseModel):
    """Conceptual message sent back to the model after tool execution."""

    model_config = ConfigDict(extra="forbid")

    tool: str = Field(min_length=1)
    result: dict[str, Any] = Field(default_factory=dict)


def normalize_tool_call(name: str, arguments: dict[str, Any] | None) -> ToolCall:
    """Normalize a provider-specific function call into our application shape."""
    return ToolCall(tool=name, arguments=arguments or {})
