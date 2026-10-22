"""Request and response shapes for authentication endpoints.

The auth router uses these Pydantic models to validate registration and login
data and to control which user fields are returned to the frontend.
"""

from pydantic import BaseModel, EmailStr
from uuid import UUID


class RegisterRequest(BaseModel):
    """Information the frontend must send to create an account."""

    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    """Credentials the frontend sends when a user signs in."""

    email: EmailStr
    password: str

class UserResponse(BaseModel):
    """Safe user information returned by the API; no password hash is exposed."""

    id: UUID
    name: str
    email: EmailStr

    model_config = {
        "from_attributes": True
    }

class LoginResponse(BaseModel):
    """JWT access token returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"
