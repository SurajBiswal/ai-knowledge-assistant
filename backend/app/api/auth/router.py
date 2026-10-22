"""Authentication HTTP endpoints.

This router accepts registration and login requests, creates ``AuthService``
with a request-scoped database session, and exposes the current authenticated
user. Business rules stay in the service and repository layers.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.database.session import get_db

from app.repositories.user_repository import (
    UserRepository,
)

from app.services.auth_service import (
    AuthService,
)

from app.api.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    LoginResponse,
)

from app.core.dependencies import (
    get_current_user,
)

from app.models.user import User

# All routes in this object are available under /api/auth.
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

# Build the service and repository with the database session for this request.
def get_auth_service(
    db: Session = Depends(get_db),
) -> AuthService:
    """Build ``AuthService`` with the database session for this request."""

    return AuthService(
        UserRepository(db)
    )

# Validate the request and ask AuthService to create a new user.
@router.post(
    "/register",
    response_model=UserResponse,
)
def register(
    request: RegisterRequest,
    service: AuthService = Depends(
        get_auth_service
    ),
):
    """Create an account and return the new user's public fields."""
    try:
        return service.register_user(
            name=request.name,
            email=request.email,
            password=request.password,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    
# Check the supplied credentials and return a signed access token.
@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    request: LoginRequest,
    service: AuthService = Depends(
        get_auth_service
    ),
):
    """Authenticate a user and return the JWT used by protected routes."""
    try:
        token = (
            service.authenticate_user(
                email=request.email,
                password=request.password,
            )
        )

        return {
            "access_token": token,
            "token_type": "bearer",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
        )
    
    
@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(
        get_current_user
    ),
):
    """Return the user loaded from the JWT by ``get_current_user``."""
    return current_user
