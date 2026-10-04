"""Gemini implementation of the provider-neutral tool-calling contract."""

from __future__ import annotations

from typing import Any, Sequence

from google import genai
from google.genai import types

from app.core.config import settings
from app.llm.base import (
    ConversationMessage,
    LLMProviderError,
    ModelResponse,
    ToolCall,
    ToolCallingConversation,
    ToolCallingLLM,
    ToolDefinition,
)


class GeminiToolCallingLLM(ToolCallingLLM):
    """Adapter for the application's existing Gemini tool-calling behavior."""

    def __init__(
        self,
        *,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.client = client or genai.Client(
            api_key=api_key or settings.GEMINI_API_KEY,
        )

    def generate(
        self,
        conversation: ToolCallingConversation,
        tools: Sequence[ToolDefinition],
    ) -> ModelResponse:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=self._to_gemini_contents(conversation),
                config=types.GenerateContentConfig(
                    system_instruction=self._system_instruction(conversation),
                    tools=self._to_gemini_tools(tools),
                    automatic_function_calling=(
                        types.AutomaticFunctionCallingConfig(disable=True)
                    ),
                ),
            )
        except Exception as exc:
            raise LLMProviderError("Gemini model request failed.") from exc

        tool_calls = tuple(
            ToolCall(
                name=call.name,
                arguments=dict(call.args or {}),
                call_id=getattr(call, "id", None),
            )
            for call in (getattr(response, "function_calls", None) or [])
        )
        text = getattr(response, "text", None)

        if not text and not tool_calls:
            raise LLMProviderError(
                "Gemini returned neither text nor tool calls."
            )

        model_response = ModelResponse(text=text, tool_calls=tool_calls)
        conversation.messages.append(
            ConversationMessage(
                role="assistant",
                text=text,
                tool_calls=tool_calls,
            )
        )
        return model_response

    @staticmethod
    def _to_gemini_tools(
        tools: Sequence[ToolDefinition],
    ) -> list[types.Tool]:
        declarations = [
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters_json_schema=dict(tool.parameters),
            )
            for tool in tools
        ]

        return [types.Tool(function_declarations=declarations)] if declarations else []

    @staticmethod
    def _to_gemini_contents(
        conversation: ToolCallingConversation,
    ) -> list[types.Content]:
        contents: list[types.Content] = []

        for message in conversation.messages:
            if message.role == "system":
                continue

            if message.role == "user":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part(text=message.text or "")],
                    )
                )
                continue

            if message.role == "assistant":
                parts = []
                if message.text:
                    parts.append(types.Part(text=message.text))
                parts.extend(
                    types.Part(
                        function_call=types.FunctionCall(
                            name=tool_call.name,
                            args=dict(tool_call.arguments),
                        )
                    )
                    for tool_call in message.tool_calls
                )
                contents.append(types.Content(role="model", parts=parts))
                continue

            parts = [
                types.Part.from_function_response(
                    name=tool_result.name,
                    response=dict(tool_result.result),
                )
                for tool_result in message.tool_results
            ]
            contents.append(types.Content(role="tool", parts=parts))

        return contents

    @staticmethod
    def _system_instruction(
        conversation: ToolCallingConversation,
    ) -> str | None:
        instructions = [
            message.text
            for message in conversation.messages
            if message.role == "system" and message.text
        ]
        return "\n\n".join(instructions) or None
