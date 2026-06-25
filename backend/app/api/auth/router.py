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

# Router for authentication endpoints 
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

# Dependency to get the AuthService instance
def get_auth_service(
    db: Session = Depends(get_db),
) -> AuthService:
    return AuthService(
        UserRepository(db)
    )

# Register endpoint
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
    
# Login endpoint
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
    return current_user