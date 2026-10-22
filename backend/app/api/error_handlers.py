"""Return validation errors without echoing submitted request values.

FastAPI's default validation response includes the rejected input. That is
unsafe for endpoints accepting API keys or bearer tokens, so this handler keeps
the familiar ``detail`` list while omitting input values and exception context.
"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def safe_validation_exception_handler(
    _request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    """Return locations and messages without returning secret-bearing input."""
    safe_errors = [
        {
            "type": item.get("type", "validation_error"),
            "loc": item.get("loc", ()),
            "msg": item.get("msg", "Invalid request value."),
        }
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": safe_errors})
