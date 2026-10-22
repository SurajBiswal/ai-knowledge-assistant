"""Run a deliberately blocked stdio MCP server for cleanup testing.

The synchronous tool blocks the server event loop long enough that graceful
protocol cleanup cannot help. The runtime test verifies that MCP's stdio
transport termination path still removes the child process within a deadline.
"""

from __future__ import annotations

import os
from pathlib import Path
import time

from mcp.server.mcpserver import MCPServer


server = MCPServer(
    name="knowledge-ai-blocking-test",
    description="A deliberately blocked local server used only by tests.",
)


@server.tool(description="Block long enough to force client-side cleanup.")
def block() -> str:
    """Block the child process so its cleanup must terminate the process."""
    time.sleep(60)
    return "unexpected completion"


if __name__ == "__main__":
    pid_file = os.getenv("MCP_TEST_PID_FILE")
    if pid_file:
        Path(pid_file).write_text(str(os.getpid()), encoding="utf-8")
    server.run(transport="stdio")
