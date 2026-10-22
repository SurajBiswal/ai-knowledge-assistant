"""Reusable FastAPI dependencies for authenticated requests.

``get_current_user`` reads the bearer token, verifies it with security helpers,
and loads the matching User through UserRepository. Protected routers depend on
this function instead of trusting a user ID supplied by the frontend.
"""

from uuid import UUID

from fastapi import (
    Depends,
    HTTPException,
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.core.security import verify_token

from app.repositories.user_repository import (
    UserRepository,
)

# FastAPI uses this object to read the Authorization: Bearer header.
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
    db: Session = Depends(get_db),
):
    """Return the database user identified by a valid JWT access token."""
    token = credentials.credentials

    try:
        user_id = verify_token(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    user_repository = UserRepository(db)
    user = user_repository.get_by_id(
        UUID(user_id)
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return user
