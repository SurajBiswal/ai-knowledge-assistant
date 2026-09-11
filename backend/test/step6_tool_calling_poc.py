"""Step 6: manual Gemini function-calling protocol proof of concept.

This is intentionally NOT a production tool and does not use the Week 9
Tool Registry. It demonstrates the protocol boundary:

User -> Gemini + tool definition -> function call -> application execution
     -> function response -> Gemini -> final answer

Run from the backend directory:

    python step6_tool_calling_poc.py

Requires GEMINI_API_KEY (or GOOGLE_API_KEY) and google-genai installed.
"""

from __future__ import annotations

from google import genai
from google.genai import types
from app.core.config import Settings

from app.tools.protocol import normalize_tool_call


MODEL = "gemini-2.5-flash"


def demo_get_workspace_stats() -> dict[str, int]:
    """Temporary demo implementation used only to prove the protocol."""
    return {
        "documents": 12,
        "chunks": 1847,
        "conversations": 34,
        "messages": 421,
    }


def build_tool_declaration() -> types.Tool:
    """Expose only the tool schema to Gemini; execution stays in our app."""
    declaration = types.FunctionDeclaration(
        name="get_workspace_stats",
        description=(
            "Return read-only statistics for the user's knowledge "
            "workspace, including document, chunk, conversation, "
            "and message counts."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {},
        },
    )
    return types.Tool(function_declarations=[declaration])


def run() -> None:

    client = genai.Client(api_key=Settings.GEMINI_API_KEY)

    user_prompt = "How many documents have I uploaded to my workspace?"

    # IMPORTANT:
    # Automatic function calling is disabled. Gemini can request a function,
    # but the SDK will NOT execute our Python function for us.
    config = types.GenerateContentConfig(
        tools=[build_tool_declaration()],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
    )

    print("\n1. USER")
    print(user_prompt)

    first_response = client.models.generate_content(
        model=MODEL,
        contents=user_prompt,
        config=config,
    )

    function_calls = first_response.function_calls or []

    if not function_calls:
        print("\nGemini answered without a tool:")
        print(first_response.text)
        client.close()
        return

    function_call = function_calls[0]
    tool_call = normalize_tool_call(
        name=function_call.name,
        arguments=dict(function_call.args or {}),
    )

    print("\n2. STRUCTURED TOOL CALL FROM GEMINI")
    print(tool_call.model_dump_json(indent=2))

    # Application boundary: validate/route/execute happens here.
    if tool_call.tool != "get_workspace_stats":
        raise RuntimeError(f"Unknown demo tool: {tool_call.tool}")

    # This is the only place the application executes the demo capability.
    tool_output = demo_get_workspace_stats()

    print("\n3. APPLICATION TOOL RESULT")
    print(tool_output)

    function_response_part = types.Part.from_function_response(
        name=tool_call.tool,
        response={"result": tool_output},
    )

    function_response_content = types.Content(
        role="tool",
        parts=[function_response_part],
    )

    # Send the model's original function-call content plus our tool result
    # back to Gemini so it can produce the natural-language answer.
    final_response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_prompt)],
            ),
            first_response.candidates[0].content,
            function_response_content,
        ],
        config=config,
    )

    print("\n4. FINAL NATURAL-LANGUAGE ANSWER")
    print(final_response.text)

    client.close()


if __name__ == "__main__":
    run()
