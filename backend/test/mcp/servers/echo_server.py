"""Run a tiny MCP 2.x server used by the real stdio integration test.

The test launches this file in a separate Python process. The ``echo`` tool
returns its input unchanged apart from a clear prefix, which makes discovery
and invocation easy to verify without using a database or external service.
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer


# MCPServer is the MCP 2.x replacement for the older FastMCP class.
server = MCPServer(
    name="knowledge-ai-stdio-test",
    description="A local echo server used only by backend integration tests.",
)


# The SDK builds the tool's JSON input schema from this function signature.
@server.tool(description="Return the supplied text with an Echo prefix.")
def echo(text: str) -> str:
    """Return a predictable response so the client can verify a real call."""
    return f"Echo: {text}"


# This entry point records the child PID for cleanup verification, then gives
# stdin and stdout to MCP's stdio protocol. It must never print normal output.
if __name__ == "__main__":
    pid_file = os.getenv("MCP_TEST_PID_FILE")
    if pid_file:
        Path(pid_file).write_text(str(os.getpid()), encoding="utf-8")

    server.run(transport="stdio")
