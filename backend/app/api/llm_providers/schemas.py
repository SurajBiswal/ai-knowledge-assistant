from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ProviderResponse(BaseModel):
    id: UUID
    code: str
    name: str
    protocol: str
    is_enabled: bool

    model_config = {
        "from_attributes": True
    }


class CreateProviderProfileRequest(BaseModel):
    provider_id: UUID
    profile_name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=1, max_length=1000)
    model: str = Field(min_length=1, max_length=255)
    api_key: str = Field(min_length=1)
    timeout_seconds: int = Field(default=60, gt=0)
    structured_json_responses: bool = True
    is_active: bool = False


class UpdateProviderProfileRequest(BaseModel):
    profile_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    provider_id: UUID | None = None
    base_url: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
    )
    model: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    api_key: str | None = Field(
        default=None,
        min_length=1,
    )
    timeout_seconds: int | None = Field(
        default=None,
        gt=0,
    )
    structured_json_responses: bool | None = None


class ProviderProfileResponse(BaseModel):
    id: UUID
    provider_id: UUID
    profile_name: str
    base_url: str
    model: str
    timeout_seconds: int
    structured_json_responses: bool
    is_active: bool
    api_key_configured: bool
    last_tested_at: datetime | None
    last_test_status: str | None

    model_config = {
        "from_attributes": True
    }


class DeleteProviderProfileResponse(BaseModel):
    message: str


class ProviderConnectionTestResponse(BaseModel):
    success: bool
    message: str


class ActivateProviderProfileResponse(BaseModel):
    message: str
    profile: ProviderProfileResponse