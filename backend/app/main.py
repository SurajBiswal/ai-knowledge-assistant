"""Create the FastAPI application and own process-wide MCP runtime cleanup.

This is the backend entry point used by the ASGI server. It enables frontend
CORS access, provides a health endpoint, and combines the authentication,
conversation, document, and LLM-provider routers into one application. The
lifespan creates an empty MCP runtime and closes any lazily started connections
when FastAPI shuts down; startup never launches persisted MCP servers.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.api.error_handlers import safe_validation_exception_handler
from app.api.conversations.router import (
    router as conversations_router,
)
from app.api.auth.router import (
    router as auth_router,
)

from app.api.documents.router import (
    router as documents_router,
)

from app.api.llm_providers.router import (
    router as llm_providers_router,
)
from app.api.mcp.router import router as mcp_router
from app.database.session import SessionLocal
from app.core.config import settings
from app.mcp.runtime import MCPRuntime


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Create an idle MCP runtime and bound cleanup during API shutdown."""
    runtime = MCPRuntime(
        session_factory=SessionLocal,
        remote_http_egress_protected=(
            settings.MCP_REMOTE_HTTP_EGRESS_PROTECTED
        ),
    )
    application.state.mcp_runtime = runtime
    try:
        yield
    finally:
        await runtime.shutdown()

# The ASGI application imported by Uvicorn when the backend starts.
app = FastAPI(
    title="AI Knowledge Assistant",
    lifespan=lifespan,
)
app.add_exception_handler(
    RequestValidationError,
    safe_validation_exception_handler,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    """Return a small response used to confirm that the API process is running."""
    return {
        "status": "healthy"
    }

app.include_router(conversations_router)

app.include_router(auth_router)

app.include_router(documents_router)

app.include_router(llm_providers_router)

app.include_router(mcp_router)
