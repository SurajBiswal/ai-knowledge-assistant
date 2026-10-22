"""OpenAI-compatible HTTP implementation of the tool-calling contract.

``LLMProviderFactory`` builds this client from a user's active profile. The same
HTTP format supports many providers because the endpoint URL and model name come
from the profile rather than being hardcoded in this file.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

import httpx

from app.llm.base import (
    ConversationMessage,
    LLMProviderError,
    ModelResponse,
    ToolCall,
    ToolCallingConversation,
    ToolCallingLLM,
    ToolDefinition,
)


class OpenAICompatibleToolCallingLLM(ToolCallingLLM):
    """Client for `/chat/completions` endpoints that support OpenAI tools.

    ``LLMProviderFactory`` constructs this adapter from the authenticated user's
    active profile. It uses ``httpx`` rather than a provider SDK so the
    same protocol works for Qwen, DeepSeek, OpenRouter, vLLM, and similar
    endpoints.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: int = 60,
        client: httpx.Client | Any | None = None,
    ) -> None:
        """Validate connection settings and create or reuse an HTTP client."""
        normalized_base_url = base_url.strip().rstrip("/")
        if not normalized_base_url:
            raise ValueError("Base URL cannot be empty.")
        if not model.strip():
            raise ValueError("Model cannot be empty.")
        if not api_key.strip():
            raise ValueError("API key cannot be empty.")
        if timeout_seconds <= 0:
            raise ValueError("Timeout must be greater than zero.")

        # Final URL and model are sent on every chat-completions request.
        self.endpoint = self._chat_completions_url(normalized_base_url)
        self.model = model.strip()
        # Headers contain the decrypted key only inside this runtime client.
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # Injected clients belong to the caller; internally created clients close here.
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def close(self) -> None:
        """Close the internally created HTTP client, if any."""
        if self._owns_client:
            self.client.close()

    def generate(
        self,
        conversation: ToolCallingConversation,
        tools: Sequence[ToolDefinition],
    ) -> ModelResponse:
        """Send normalized history/tools and return normalized text/tool calls."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._to_openai_messages(conversation),
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": dict(tool.parameters),
                    },
                }
                for tool in tools
            ]
            payload["tool_choice"] = "auto"

        try:
            response = self.client.post(
                self.endpoint,
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            response_payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise LLMProviderError(
                "OpenAI-compatible model request failed."
            ) from exc

        model_response = self._parse_response(response_payload)
        conversation.messages.append(
            ConversationMessage(
                role="assistant",
                text=model_response.text,
                tool_calls=model_response.tool_calls,
            )
        )
        return model_response

    @staticmethod
    def _chat_completions_url(base_url: str) -> str:
        """Accept either a base API URL or the complete chat-completions URL."""
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    @staticmethod
    def _parse_response(payload: Mapping[str, Any]) -> ModelResponse:
        """Validate provider JSON and turn it into the shared response types."""
        try:
            message = payload["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError(
                "OpenAI-compatible response did not include a message."
            ) from exc

        raw_tool_calls = message.get("tool_calls") or []
        tool_calls: list[ToolCall] = []

        for raw_tool_call in raw_tool_calls:
            function = raw_tool_call.get("function") or {}
            raw_arguments = function.get("arguments", "{}")
            try:
                arguments = (
                    raw_arguments
                    if isinstance(raw_arguments, Mapping)
                    else json.loads(raw_arguments)
                )
            except (TypeError, json.JSONDecodeError) as exc:
                raise LLMProviderError(
                    "OpenAI-compatible response contained invalid tool arguments."
                ) from exc

            if not isinstance(arguments, Mapping) or not function.get("name"):
                raise LLMProviderError(
                    "OpenAI-compatible response contained an invalid tool call."
                )

            tool_calls.append(
                ToolCall(
                    name=function["name"],
                    arguments=dict(arguments),
                    call_id=raw_tool_call.get("id"),
                )
            )

        text = message.get("content")
        if text is not None and not isinstance(text, str):
            raise LLMProviderError(
                "OpenAI-compatible response contained invalid text."
            )
        if not text and not tool_calls:
            raise LLMProviderError(
                "OpenAI-compatible response returned neither text nor tool calls."
            )

        return ModelResponse(text=text, tool_calls=tuple(tool_calls))

    @staticmethod
    def _to_openai_messages(
        conversation: ToolCallingConversation,
    ) -> list[dict[str, Any]]:
        """Convert normalized history into OpenAI-compatible message dictionaries."""
        messages: list[dict[str, Any]] = []

        for message in conversation.messages:
            if message.role == "system":
                messages.append(
                    {"role": "system", "content": message.text or ""}
                )
                continue

            if message.role == "user":
                messages.append(
                    {"role": "user", "content": message.text or ""}
                )
                continue

            if message.role == "assistant":
                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": message.text,
                }
                if message.tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": tool_call.call_id or tool_call.name,
                            "type": "function",
                            "function": {
                                "name": tool_call.name,
                                "arguments": json.dumps(
                                    dict(tool_call.arguments)
                                ),
                            },
                        }
                        for tool_call in message.tool_calls
                    ]
                messages.append(assistant_message)
                continue

            for tool_result in message.tool_results:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": (
                            tool_result.call_id or tool_result.name
                        ),
                        "content": json.dumps(dict(tool_result.result)),
                    }
                )

        return messages
