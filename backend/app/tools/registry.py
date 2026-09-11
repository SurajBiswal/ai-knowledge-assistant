from __future__ import annotations

from typing import Any


class ToolRegistry:
    """
    Central registry for application tools.

    The registry is responsible for:

    - Registering tools
    - Looking up tools by name
    - Listing available tools
    - Exposing tool metadata
    - Executing a tool by name

    The registry does NOT decide which tool should be used.

    Tool selection is the responsibility of the LLM/agent.

    Conceptually:

        tool_name
            ↓
        ToolRegistry
            ↓
        Tool instance
            ↓
        validate + execute
            ↓
        structured result
    """

    def __init__(self) -> None:
        self._tools: dict[str, Any] = {}

    def register(self, tool: Any) -> None:
        """
        Register a tool using its unique name.

        The tool must expose a `name` attribute.
        """

        tool_name = getattr(tool, "name", None)

        if not tool_name:
            raise ValueError(
                "Cannot register tool without a 'name' attribute."
            )

        if tool_name in self._tools:
            raise ValueError(
                f"Tool '{tool_name}' is already registered."
            )

        self._tools[tool_name] = tool

    def get_tool(self, name: str) -> Any:
        """
        Return a registered tool by name.
        """

        try:
            return self._tools[name]
        except KeyError as exc:
            raise ValueError(
                f"Tool '{name}' is not registered."
            ) from exc

    def list_tools(self) -> list[str]:
        """
        Return the names of all registered tools.
        """

        return list(self._tools.keys())

    def get_all_tools(self) -> dict[str, Any]:
        """
        Return all registered tools.

        A copy is returned so callers cannot modify
        the registry's internal dictionary.
        """

        return self._tools.copy()

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """
        Execute a registered tool by name.

        The registry resolves the tool.

        The tool itself remains responsible for:

        - Input validation
        - Business logic
        - Calling services/repositories
        - Returning structured output

        `context` represents application-controlled values
        such as user_id that must NOT come from the LLM.
        """

        tool = self.get_tool(name)

        return tool.execute(arguments)