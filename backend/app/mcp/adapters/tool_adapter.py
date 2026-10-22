"""Adapt one discovered MCP tool to the application's tool interface.

The Agent Node reads its name, description, and JSON input schema. The Tool Node
calls ``execute_async``, which delegates to ``MCPClientManager`` and converts the
SDK result into bounded, JSON-safe data suitable for an LLM.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.mcp.client.manager import MCPClientManager


# Limits prevent a remote server from placing huge content in model context.
MAX_TEXT_CHARS = 12_000
MAX_OUTPUT_CHARS = 24_000
# Public names are bounded for compatibility with model tool-name limits.
MAX_TOOL_NAME_CHARS = 64


@dataclass(slots=True)
class MCPToolAdapter:
    """Expose one remote MCP tool through the application's registry contract."""

    # Shared manager used to call the connected server.
    manager: MCPClientManager
    # Local configured server name and original tool name sent to that server.
    server_name: str
    remote_tool_name: str
    # Human-readable purpose and JSON argument schema discovered from MCP.
    description: str | None
    input_schema: Mapping[str, Any]
    # Safe namespaced name generated after dataclass initialization.
    name: str = field(init=False)

    def __post_init__(self) -> None:
        """Validate discovered metadata and build a collision-resistant name."""
        if not self.server_name.strip():
            raise ValueError("MCP server name cannot be empty")
        if not self.remote_tool_name.strip():
            raise ValueError("MCP tool name cannot be empty")
        if not isinstance(self.input_schema, Mapping):
            raise TypeError("MCP tool input schema must be a mapping")

        self.server_name = self.server_name.strip()
        self.remote_tool_name = self.remote_tool_name.strip()
        self.description = (
            self.description.strip()
            if self.description and self.description.strip()
            else f"MCP tool {self.remote_tool_name} from {self.server_name}."
        )
        self.name = _public_tool_name(
            server_name=self.server_name,
            tool_name=self.remote_tool_name,
        )

    def get_definition(self) -> dict[str, Any]:
        """Return name, description, and copied MCP JSON Schema for the LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": deepcopy(dict(self.input_schema)),
        }

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Reject the sync path because remote MCP calls must be awaited."""
        raise RuntimeError(
            "MCP tools require ToolRegistry.execute_async()."
        )

    async def execute_async(
        self,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Await the remote call and return safe text/structured output metadata."""
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be a dictionary")

        result = await self.manager.call_tool(
            server_name=self.server_name,
            tool_name=self.remote_tool_name,
            arguments=arguments,
        )

        normalized: dict[str, Any] = {
            "server": self.server_name,
            "tool": self.remote_tool_name,
            "is_error": bool(getattr(result, "is_error", False)),
            "content": [],
            "structured_content": None,
        }

        structured = getattr(result, "structured_content", None)
        if isinstance(structured, Mapping):
            normalized["structured_content"] = _json_safe_mapping(structured)

        for block in getattr(result, "content", []) or []:
            block_type = type(block).__name__

            if block_type == "TextContent":
                text = getattr(block, "text", "")
                if not isinstance(text, str):
                    text = str(text)
                normalized["content"].append(
                    {
                        "type": "text",
                        "text": text[:MAX_TEXT_CHARS],
                    }
                )
            elif block_type == "ImageContent":
                normalized["content"].append(
                    {
                        "type": "image",
                        "omitted": True,
                        "reason": "Binary image content is not forwarded.",
                    }
                )
            elif block_type == "AudioContent":
                normalized["content"].append(
                    {
                        "type": "audio",
                        "omitted": True,
                        "reason": "Binary audio content is not forwarded.",
                    }
                )
            else:
                normalized["content"].append(
                    {
                        "type": "unsupported",
                        "content_type": block_type,
                        "omitted": True,
                    }
                )

        encoded = json.dumps(
            normalized,
            ensure_ascii=False,
            default=str,
        )
        if len(encoded) > MAX_OUTPUT_CHARS:
            normalized["content"] = [
                {
                    "type": "text",
                    "text": (
                        "MCP output omitted because it exceeded the size limit."
                    ),
                }
            ]
            normalized["structured_content"] = None
            normalized["truncated"] = True

        return normalized


def _public_tool_name(*, server_name: str, tool_name: str) -> str:
    """Build ``mcp_server_tool`` and shorten it deterministically when needed."""
    raw_name = f"mcp_{_safe_name_part(server_name)}_{_safe_name_part(tool_name)}"
    if len(raw_name) <= MAX_TOOL_NAME_CHARS:
        return raw_name

    digest = hashlib.sha256(raw_name.encode("utf-8")).hexdigest()[:8]
    prefix_length = MAX_TOOL_NAME_CHARS - len(digest) - 1
    return f"{raw_name[:prefix_length]}_{digest}"


def _safe_name_part(value: str) -> str:
    """Replace characters unsupported by LLM tool names with underscores."""
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_-").lower()
    if not safe:
        raise ValueError("MCP names must contain an alphanumeric character")
    return safe


def _json_safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Round-trip structured content through JSON to remove SDK-only objects."""
    encoded = json.dumps(dict(value), ensure_ascii=False, default=str)
    decoded = json.loads(encoded)
    return decoded if isinstance(decoded, dict) else {}
