"""Authenticated management endpoints for user-owned MCP connections.

Routes derive ownership from the existing JWT dependency, persist changes
through ``MCPConnectionService``, and delegate all live transport work to the
lifespan-owned ``MCPRuntime``. No endpoint accepts a user ID or executes a tool.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.mcp.schemas import (
    APIKeyHeaderCredentialsRequest,
    BearerCredentialsRequest,
    CreateMCPConnectionRequest,
    DeleteMCPConnectionResponse,
    MCPConnectionResponse,
    MCPConnectionTestResponse,
    MCPDiscoveryResponse,
    MCPRuntimeActionResponse,
    MCPToolResponse,
    SetEnabledRequest,
    UpdateMCPConnectionRequest,
)
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.mcp.runtime import MCPRuntime, MCPRuntimeError, MCPRuntimeStatus
from app.models.user import User
from app.services.credential_encryption_service import (
    CredentialEncryptionService,
)
from app.services.mcp_connection_service import MCPConnectionService


router = APIRouter(prefix="/api/mcp", tags=["MCP Connections"])


def get_mcp_connection_service(
    db: Session = Depends(get_db),
) -> MCPConnectionService:
    """Build the persistence service with the current request transaction."""
    return MCPConnectionService(
        db,
        credential_encryption_service=CredentialEncryptionService(),
    )


def get_mcp_runtime(request: Request) -> MCPRuntime:
    """Return the process runtime created by FastAPI lifespan startup."""
    runtime = getattr(request.app.state, "mcp_runtime", None)
    if not isinstance(runtime, MCPRuntime):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "runtime_unavailable",
                "message": "MCP runtime is unavailable.",
            },
        )
    return runtime


def _credentials_mapping(request_credentials: Any) -> dict[str, str] | None:
    """Reveal a typed SecretStr only while passing it to encryption logic."""
    if request_credentials is None:
        return None
    if isinstance(request_credentials, BearerCredentialsRequest):
        return {"token": request_credentials.token.get_secret_value()}
    if isinstance(request_credentials, APIKeyHeaderCredentialsRequest):
        return {
            "header_name": request_credentials.header_name,
            "api_key": request_credentials.api_key.get_secret_value(),
        }
    raise HTTPException(status_code=400, detail="Invalid MCP credentials.")


def _commit(db: Session) -> None:
    """Commit one API mutation and translate uniqueness races safely."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MCP connection conflicts with an existing record.",
        ) from None


def _service_error(error: ValueError) -> HTTPException:
    """Map owned-resource misses to 404 and safe validation failures to 400."""
    message = str(error)
    return HTTPException(
        status_code=(
            status.HTTP_404_NOT_FOUND
            if message in {"MCP connection not found.", "MCP tool not found."}
            else status.HTTP_400_BAD_REQUEST
        ),
        detail=message,
    )


def _runtime_error(error: MCPRuntimeError) -> HTTPException:
    """Expose only the runtime's stable code and credential-free message."""
    if error.code in {"connection_not_found", "tool_not_found"}:
        response_status = status.HTTP_404_NOT_FOUND
    elif error.code in {
        "connection_timeout",
        "operation_timeout",
        "authorization_timeout",
    }:
        response_status = status.HTTP_504_GATEWAY_TIMEOUT
    elif error.code in {"runtime_stopped"}:
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        response_status = status.HTTP_409_CONFLICT
    return HTTPException(
        status_code=response_status,
        detail={"code": error.code, "message": str(error)},
    )


def _runtime_response(result: MCPRuntimeStatus) -> MCPRuntimeActionResponse:
    """Copy only safe process-local status fields into the public response."""
    return MCPRuntimeActionResponse(
        connection_id=result.connection_id,
        state=result.state,
        tool_count=result.tool_count,
    )


def _record_runtime_failure(
    *,
    service: MCPConnectionService,
    db: Session,
    user_id: UUID,
    connection_id: UUID,
    error: MCPRuntimeError,
) -> None:
    """Persist only a stable error code after an owned runtime operation fails."""
    try:
        service.record_test_result(
            connection_id=connection_id,
            user_id=user_id,
            success=False,
            error_code=error.code,
        )
        _commit(db)
    except ValueError:
        db.rollback()


@router.post(
    "/connections",
    response_model=MCPConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_connection(
    payload: CreateMCPConnectionRequest,
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
    db: Session = Depends(get_db),
) -> MCPConnectionResponse:
    """Create a disabled connection owned by the authenticated user."""
    try:
        connection = service.create_connection(
            user_id=current_user.id,
            name=payload.name,
            transport=payload.transport,
            server_url=payload.server_url,
            stdio_template_code=payload.stdio_template_code,
            configuration=payload.configuration,
            auth_type=payload.auth_type,
            credentials=_credentials_mapping(payload.credentials),
            timeout_seconds=payload.timeout_seconds,
        )
        _commit(db)
        return MCPConnectionResponse.model_validate(connection)
    except ValueError as error:
        raise _service_error(error) from None


@router.get("/connections", response_model=list[MCPConnectionResponse])
def list_connections(
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
) -> list[MCPConnectionResponse]:
    """List redacted connection definitions owned by the current user."""
    return [
        MCPConnectionResponse.model_validate(item)
        for item in service.list_connections(user_id=current_user.id)
    ]


@router.get(
    "/connections/{connection_id}",
    response_model=MCPConnectionResponse,
)
def get_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
) -> MCPConnectionResponse:
    """Retrieve one connection only when it belongs to the current user."""
    try:
        return MCPConnectionResponse.model_validate(
            service.get_connection(
                connection_id=connection_id,
                user_id=current_user.id,
            )
        )
    except ValueError as error:
        raise _service_error(error) from None


@router.patch(
    "/connections/{connection_id}",
    response_model=MCPConnectionResponse,
)
async def update_connection(
    connection_id: UUID,
    payload: UpdateMCPConnectionRequest,
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
    runtime: MCPRuntime = Depends(get_mcp_runtime),
    db: Session = Depends(get_db),
) -> MCPConnectionResponse:
    """Commit validated settings before invalidating any old live client."""
    if not payload.model_fields_set:
        raise HTTPException(status_code=400, detail="No update fields supplied.")
    updates: dict[str, Any] = {}
    for field_name in payload.model_fields_set:
        if field_name == "credentials":
            updates[field_name] = _credentials_mapping(payload.credentials)
        else:
            updates[field_name] = getattr(payload, field_name)
    try:
        service.update_connection(
            connection_id=connection_id,
            user_id=current_user.id,
            updates=updates,
        )
        _commit(db)
        await runtime.invalidate_connection(
            user_id=current_user.id,
            connection_id=connection_id,
        )
        refreshed = service.get_connection(
            connection_id=connection_id,
            user_id=current_user.id,
        )
        return MCPConnectionResponse.model_validate(refreshed)
    except ValueError as error:
        raise _service_error(error) from None
    except MCPRuntimeError as error:
        raise _runtime_error(error) from None


@router.delete(
    "/connections/{connection_id}",
    response_model=DeleteMCPConnectionResponse,
)
async def delete_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
    runtime: MCPRuntime = Depends(get_mcp_runtime),
    db: Session = Depends(get_db),
) -> DeleteMCPConnectionResponse:
    """Disable first, close live state, then remove the persisted definition."""
    try:
        service.get_connection(
            connection_id=connection_id,
            user_id=current_user.id,
        )
        service.set_connection_enabled(
            connection_id=connection_id,
            user_id=current_user.id,
            enabled=False,
        )
        _commit(db)
        await runtime.invalidate_connection(
            user_id=current_user.id,
            connection_id=connection_id,
        )
        service.delete_connection(
            connection_id=connection_id,
            user_id=current_user.id,
        )
        _commit(db)
        return DeleteMCPConnectionResponse(
            deleted=True,
            connection_id=connection_id,
        )
    except ValueError as error:
        raise _service_error(error) from None
    except MCPRuntimeError as error:
        raise _runtime_error(error) from None


@router.patch(
    "/connections/{connection_id}/enabled",
    response_model=MCPConnectionResponse,
)
async def set_connection_enabled(
    connection_id: UUID,
    payload: SetEnabledRequest,
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
    runtime: MCPRuntime = Depends(get_mcp_runtime),
    db: Session = Depends(get_db),
) -> MCPConnectionResponse:
    """Commit connection availability and close any stale local runtime."""
    try:
        service.set_connection_enabled(
            connection_id=connection_id,
            user_id=current_user.id,
            enabled=payload.enabled,
        )
        _commit(db)
        await runtime.invalidate_connection(
            user_id=current_user.id,
            connection_id=connection_id,
        )
        return MCPConnectionResponse.model_validate(
            service.get_connection(
                connection_id=connection_id,
                user_id=current_user.id,
            )
        )
    except ValueError as error:
        raise _service_error(error) from None
    except MCPRuntimeError as error:
        raise _runtime_error(error) from None


@router.post(
    "/connections/{connection_id}/connect",
    response_model=MCPRuntimeActionResponse,
)
async def connect_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
    runtime: MCPRuntime = Depends(get_mcp_runtime),
    db: Session = Depends(get_db),
) -> MCPRuntimeActionResponse:
    """Explicitly start one owned enabled connection through the runtime."""
    try:
        service.get_connection(
            connection_id=connection_id,
            user_id=current_user.id,
        )
        result = await runtime.connect(
            user_id=current_user.id,
            connection_id=connection_id,
        )
        service.record_test_result(
            connection_id=connection_id,
            user_id=current_user.id,
            success=True,
        )
        _commit(db)
        return _runtime_response(result)
    except ValueError as error:
        raise _service_error(error) from None
    except MCPRuntimeError as error:
        _record_runtime_failure(
            service=service,
            db=db,
            user_id=current_user.id,
            connection_id=connection_id,
            error=error,
        )
        raise _runtime_error(error) from None


@router.post(
    "/connections/{connection_id}/disconnect",
    response_model=MCPRuntimeActionResponse,
)
async def disconnect_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
    runtime: MCPRuntime = Depends(get_mcp_runtime),
) -> MCPRuntimeActionResponse:
    """Explicitly close one owned runtime without deleting its definition."""
    try:
        service.get_connection(
            connection_id=connection_id,
            user_id=current_user.id,
        )
        return _runtime_response(
            await runtime.disconnect(
                user_id=current_user.id,
                connection_id=connection_id,
            )
        )
    except ValueError as error:
        raise _service_error(error) from None
    except MCPRuntimeError as error:
        raise _runtime_error(error) from None


@router.post(
    "/connections/{connection_id}/test",
    response_model=MCPConnectionTestResponse,
)
async def test_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
    runtime: MCPRuntime = Depends(get_mcp_runtime),
    db: Session = Depends(get_db),
) -> MCPConnectionTestResponse:
    """Explicitly connect, discover, and disconnect while persisting readiness."""
    try:
        service.get_connection(
            connection_id=connection_id,
            user_id=current_user.id,
        )
        connected = await runtime.connect(
            user_id=current_user.id,
            connection_id=connection_id,
        )
        await runtime.disconnect(
            user_id=current_user.id,
            connection_id=connection_id,
        )
        service.record_test_result(
            connection_id=connection_id,
            user_id=current_user.id,
            success=True,
        )
        _commit(db)
        return MCPConnectionTestResponse(
            success=True,
            status="ready",
            tool_count=connected.tool_count,
        )
    except ValueError as error:
        raise _service_error(error) from None
    except MCPRuntimeError as error:
        _record_runtime_failure(
            service=service,
            db=db,
            user_id=current_user.id,
            connection_id=connection_id,
            error=error,
        )
        raise _runtime_error(error) from None


@router.post(
    "/connections/{connection_id}/refresh-tools",
    response_model=MCPDiscoveryResponse,
)
async def refresh_tools(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
    runtime: MCPRuntime = Depends(get_mcp_runtime),
    db: Session = Depends(get_db),
) -> MCPDiscoveryResponse:
    """Explicitly refresh one server's untrusted discovery metadata."""
    try:
        service.get_connection(
            connection_id=connection_id,
            user_id=current_user.id,
        )
        tools = await runtime.refresh_tools(
            user_id=current_user.id,
            connection_id=connection_id,
        )
        service.record_test_result(
            connection_id=connection_id,
            user_id=current_user.id,
            success=True,
        )
        _commit(db)
        return MCPDiscoveryResponse(
            connection_id=connection_id,
            tools=[MCPToolResponse.model_validate(item) for item in tools],
        )
    except ValueError as error:
        raise _service_error(error) from None
    except MCPRuntimeError as error:
        _record_runtime_failure(
            service=service,
            db=db,
            user_id=current_user.id,
            connection_id=connection_id,
            error=error,
        )
        raise _runtime_error(error) from None


@router.get(
    "/connections/{connection_id}/tools",
    response_model=list[MCPToolResponse],
)
def list_tools(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
) -> list[MCPToolResponse]:
    """List persisted tools only through their owned parent connection."""
    try:
        return [
            MCPToolResponse.model_validate(item)
            for item in service.list_tools(
                connection_id=connection_id,
                user_id=current_user.id,
            )
        ]
    except ValueError as error:
        raise _service_error(error) from None


@router.get(
    "/connections/{connection_id}/tools/{tool_id}",
    response_model=MCPToolResponse,
)
def get_tool(
    connection_id: UUID,
    tool_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
) -> MCPToolResponse:
    """Retrieve one tool after checking tool, connection, and user together."""
    try:
        return MCPToolResponse.model_validate(
            service.get_tool(
                connection_id=connection_id,
                tool_id=tool_id,
                user_id=current_user.id,
            )
        )
    except ValueError as error:
        raise _service_error(error) from None


@router.patch(
    "/connections/{connection_id}/tools/{tool_id}/enabled",
    response_model=MCPToolResponse,
)
def set_tool_enabled(
    connection_id: UUID,
    tool_id: UUID,
    payload: SetEnabledRequest,
    current_user: User = Depends(get_current_user),
    service: MCPConnectionService = Depends(get_mcp_connection_service),
    db: Session = Depends(get_db),
) -> MCPToolResponse:
    """Persist explicit approval for one available tool owned by the user."""
    try:
        tool = service.set_tool_enabled(
            connection_id=connection_id,
            tool_id=tool_id,
            user_id=current_user.id,
            enabled=payload.enabled,
        )
        _commit(db)
        return MCPToolResponse.model_validate(tool)
    except ValueError as error:
        raise _service_error(error) from None
