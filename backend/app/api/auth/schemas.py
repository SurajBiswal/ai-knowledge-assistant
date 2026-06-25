from pydantic import BaseModel, EmailStr
from uuid import UUID


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr

    model_config = {
        "from_attributes": True
    }

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"