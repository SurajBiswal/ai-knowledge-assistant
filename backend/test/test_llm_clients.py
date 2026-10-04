from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.llm.base import (
    KNOWLEDGE_AI_SYSTEM_PROMPT,
    LLMProviderError,
    ToolDefinition,
    ToolResult,
)
from app.llm.gemini import GeminiToolCallingLLM
from app.llm.openai_compatible import OpenAICompatibleToolCallingLLM


TOOL = ToolDefinition(
    name="search_documents",
    description="Search the authenticated user's documents.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
        },
        "required": ["query"],
    },
)


class FakeGeminiModels:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeGeminiClient:
    def __init__(self, responses: list[object]) -> None:
        self.models = FakeGeminiModels(responses)


class FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeHTTPClient:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = payloads
        self.calls: list[dict] = []
        self.closed = False

    def post(self, url: str, **kwargs) -> FakeHTTPResponse:
        self.calls.append({"url": url, **kwargs})
        return FakeHTTPResponse(self.payloads.pop(0))

    def close(self) -> None:
        self.closed = True


def test_gemini_adapter_preserves_tool_calling_conversation() -> None:
    client = FakeGeminiClient(
        responses=[
            SimpleNamespace(
                text=None,
                function_calls=[
                    SimpleNamespace(
                        id="gemini-call-1",
                        name="search_documents",
                        args={"query": "device"},
                    )
                ],
            ),
            SimpleNamespace(text="The device revealed the location.", function_calls=[]),
        ]
    )
    llm = GeminiToolCallingLLM(client=client)
    conversation = llm.start_conversation("What did the device reveal?")

    first_response = llm.generate(conversation, [TOOL])

    assert first_response.text is None
    assert first_response.tool_calls[0].name == "search_documents"
    assert first_response.tool_calls[0].call_id == "gemini-call-1"

    llm.add_tool_results(
        conversation,
        [
            ToolResult(
                name="search_documents",
                call_id="gemini-call-1",
                result={"results": [{"text": "location"}]},
            )
        ],
    )
    second_response = llm.generate(conversation, [TOOL])

    assert second_response.text == "The device revealed the location."
    second_request = client.models.calls[1]
    assert [content.role for content in second_request["contents"]] == [
        "user",
        "model",
        "tool",
    ]
    assert second_request["config"].system_instruction == (
        KNOWLEDGE_AI_SYSTEM_PROMPT
    )


def test_openai_compatible_adapter_maps_tool_loop_to_chat_completions() -> None:
    client = FakeHTTPClient(
        payloads=[
            {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "type": "function",
                                    "function": {
                                        "name": "search_documents",
                                        "arguments": '{"query":"device"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": "The device revealed the location.",
                        }
                    }
                ]
            },
        ]
    )
    llm = OpenAICompatibleToolCallingLLM(
        base_url="https://example.test/v1/",
        model="qwen-test",
        api_key="test-key",
        client=client,
    )
    conversation = llm.start_conversation("What did the device reveal?")

    first_response = llm.generate(conversation, [TOOL])

    assert client.calls[0]["url"] == "https://example.test/v1/chat/completions"
    assert client.calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert client.calls[0]["json"]["tools"][0]["function"]["name"] == (
        "search_documents"
    )
    assert first_response.tool_calls[0].call_id == "call_123"
    assert first_response.tool_calls[0].arguments == {"query": "device"}

    llm.add_tool_results(
        conversation,
        [
            ToolResult(
                name="search_documents",
                call_id="call_123",
                result={"results": [{"text": "location"}]},
            )
        ],
    )
    second_response = llm.generate(conversation, [TOOL])

    assert second_response.text == "The device revealed the location."
    second_messages = client.calls[1]["json"]["messages"]
    assert [message["role"] for message in second_messages] == [
        "system",
        "user",
        "assistant",
        "tool",
    ]
    assert second_messages[0]["content"] == KNOWLEDGE_AI_SYSTEM_PROMPT
    assert second_messages[-1]["tool_call_id"] == "call_123"


def test_openai_compatible_adapter_rejects_invalid_tool_arguments() -> None:
    client = FakeHTTPClient(
        payloads=[
            {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "function": {
                                        "name": "search_documents",
                                        "arguments": "not-json",
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    )
    llm = OpenAICompatibleToolCallingLLM(
        base_url="https://example.test/v1",
        model="qwen-test",
        api_key="test-key",
        client=client,
    )

    with pytest.raises(LLMProviderError, match="invalid tool arguments"):
        llm.generate(llm.start_conversation("Find it"), [TOOL])


def test_adapter_validates_required_configuration() -> None:
    with pytest.raises(ValueError, match="Base URL cannot be empty"):
        OpenAICompatibleToolCallingLLM(
            base_url=" ",
            model="model",
            api_key="test-key",
        )
