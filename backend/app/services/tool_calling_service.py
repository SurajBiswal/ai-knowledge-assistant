from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.tools.registry import ToolRegistry


MODEL_NAME = "gemini-2.5-flash"


class ToolCallingService:
    """
    Handles Gemini structured function calling.

    Part 7 responsibility split:

        Agent Node
            ↓
        ToolCallingService
            ↓
        Gemini

    Gemini may return:

        1. Final text response

        OR

        2. Structured tool calls

    Tool execution itself is NOT performed here.

    Tool execution is now handled by the LangGraph Tool Node.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        client: genai.Client | None = None,
    ) -> None:
        self.tool_registry = tool_registry

        self.client = client or genai.Client(
            api_key=settings.GEMINI_API_KEY,
        )

    def create_initial_contents(
        self,
        query: str,
    ) -> list[Any]:
        """
        Create the initial Gemini conversation contents.
        """

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        return [
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=query.strip(),
                    )
                ],
            )
        ]

    def call_model(
        self,
        contents: list[Any],
    ) -> Any:
        """
        Call Gemini with the application's registered tools.

        Gemini decides whether:

        - a tool is needed
        - no tool is needed

        Tool execution is handled outside this service
        by the LangGraph Tool Node.
        """

        tools = self._build_gemini_tools()

        return self.client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                tools=tools,
                automatic_function_calling=(
                    types.AutomaticFunctionCallingConfig(
                        disable=True,
                    )
                ),
            ),
        )

    @staticmethod
    def extract_tool_calls(
        response: Any,
    ) -> list[dict[str, Any]]:
        """
        Extract structured tool calls from Gemini response.
        """

        function_calls = response.function_calls

        if not function_calls:
            return []

        tool_calls: list[dict[str, Any]] = []

        for function_call in function_calls:

            tool_calls.append(
                {
                    "name": function_call.name,
                    "arguments": dict(
                        function_call.args or {}
                    ),
                }
            )

        return tool_calls

    @staticmethod
    def extract_final_response(
        response: Any,
    ) -> str:
        """
        Extract Gemini's final natural-language response.
        """

        text = response.text

        if not text:
            raise RuntimeError(
                "Gemini returned neither a function call "
                "nor a text response."
            )

        return text

    @staticmethod
    def get_model_content(
        response: Any,
    ) -> types.Content:
        """
        Extract Gemini's exact model content.

        This is required when Gemini produced a function call.

        The function-call message must be preserved before
        sending the corresponding function-response message.
        """

        candidates = response.candidates

        if not candidates:
            raise RuntimeError(
                "Gemini returned no candidates."
            )

        content = candidates[0].content

        if content is None:
            raise RuntimeError(
                "Gemini response has no content."
            )

        return content

    @staticmethod
    def create_tool_result_content(
        tool_results: list[dict[str, Any]],
    ) -> types.Content:
        """
        Convert application tool results into Gemini
        function-response messages.
        """

        parts = []

        for tool_result in tool_results:

            parts.append(
                types.Part.from_function_response(
                    name=tool_result["name"],
                    response=tool_result["result"],
                )
            )

        return types.Content(
            role="tool",
            parts=parts,
        )

    @staticmethod
    def serialize_tool_result(
        result: Any,
    ) -> dict[str, Any]:
        """
        Convert tool output into JSON-compatible data.
        """

        if hasattr(result, "model_dump"):
            return result.model_dump(
                mode="json"
            )

        if isinstance(result, dict):
            return result

        raise TypeError(
            "Tool result must be a Pydantic model "
            "or dictionary."
        )

    def _build_gemini_tools(
        self,
    ) -> list[types.Tool]:
        """
        Convert registered application tools into Gemini
        function declarations.

        Tool input schema
            ↓
        Pydantic JSON Schema
            ↓
        Gemini FunctionDeclaration
        """

        function_declarations = []

        for tool in (
            self.tool_registry
            .get_all_tools()
            .values()
        ):

            input_schema = tool.input_schema

            parameters_json_schema = (
                input_schema.model_json_schema()
            )

            function_declarations.append(
                types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters_json_schema=(
                        parameters_json_schema
                    ),
                )
            )

        return [
            types.Tool(
                function_declarations=(
                    function_declarations
                )
            )
        ]