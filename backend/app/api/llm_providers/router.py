from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.core.dependencies import (
    get_current_user,
)

from app.models.user import User

from app.repositories.llm_provider_profile_repository import (
    LLMProviderProfileRepository,
)

from app.repositories.llm_provider_repository import (
    LLMProviderRepository,
)

from app.services.credential_encryption_service import (
    CredentialEncryptionService,
)

from app.services.llm_provider_service import (
    LLMProviderService,
)

from app.api.llm_providers.schemas import (
    ActivateProviderProfileResponse,
    CreateProviderProfileRequest,
    DeleteProviderProfileResponse,
    ProviderConnectionTestResponse,
    ProviderProfileResponse,
    ProviderResponse,
    UpdateProviderProfileRequest,
)


router = APIRouter(
    prefix="/api/ai",
    tags=["AI Providers"],
)


def get_llm_provider_service(
    db: Session = Depends(get_db),
) -> LLMProviderService:
    return LLMProviderService(
        db=db,
        credential_encryption_service=CredentialEncryptionService(),
    )


def _to_provider_profile_response(
    profile,
) -> ProviderProfileResponse:
    return ProviderProfileResponse(
        id=profile.id,
        provider_id=profile.provider_id,
        profile_name=profile.profile_name,
        base_url=profile.base_url,
        model=profile.model,
        timeout_seconds=profile.timeout_seconds,
        structured_json_responses=profile.structured_json_responses,
        is_active=profile.is_active,
        api_key_configured=bool(profile.encrypted_api_key),
        last_tested_at=profile.last_tested_at,
        last_test_status=profile.last_test_status,
    )


@router.get(
    "/providers",
    response_model=list[ProviderResponse],
)
def list_providers(
    current_user: User = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    provider_repository = LLMProviderRepository(db)

    return provider_repository.list_enabled()


@router.get(
    "/provider-profiles",
    response_model=list[ProviderProfileResponse],
)
def list_provider_profiles(
    current_user: User = Depends(
        get_current_user,
    ),
    service: LLMProviderService = Depends(
        get_llm_provider_service,
    ),
):
    profiles = service.list_profiles(
        user_id=current_user.id,
    )

    return [
        _to_provider_profile_response(profile)
        for profile in profiles
    ]


@router.post(
    "/provider-profiles",
    response_model=ProviderProfileResponse,
)
def create_provider_profile(
    request: CreateProviderProfileRequest,
    current_user: User = Depends(
        get_current_user,
    ),
    service: LLMProviderService = Depends(
        get_llm_provider_service,
    ),
):
    try:
        profile = service.create_profile(
            user_id=current_user.id,
            provider_id=request.provider_id,
            profile_name=request.profile_name,
            base_url=request.base_url,
            model=request.model,
            api_key=request.api_key,
            timeout_seconds=request.timeout_seconds,
            structured_json_responses=request.structured_json_responses,
            is_active=request.is_active,
        )

        return _to_provider_profile_response(profile)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.get(
    "/provider-profiles/{profile_id}",
    response_model=ProviderProfileResponse,
)
def get_provider_profile(
    profile_id: UUID,
    current_user: User = Depends(
        get_current_user,
    ),
    service: LLMProviderService = Depends(
        get_llm_provider_service,
    ),
):
    try:
        profile = service.get_profile(
            profile_id=profile_id,
            user_id=current_user.id,
        )

        return _to_provider_profile_response(profile)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@router.put(
    "/provider-profiles/{profile_id}",
    response_model=ProviderProfileResponse,
)
def update_provider_profile(
    profile_id: UUID,
    request: UpdateProviderProfileRequest,
    current_user: User = Depends(
        get_current_user,
    ),
    service: LLMProviderService = Depends(
        get_llm_provider_service,
    ),
):
    try:
        profile = service.update_profile(
            profile_id=profile_id,
            user_id=current_user.id,
            profile_name=request.profile_name,
            provider_id=request.provider_id,
            base_url=request.base_url,
            model=request.model,
            api_key=request.api_key,
            timeout_seconds=request.timeout_seconds,
            structured_json_responses=request.structured_json_responses,
        )

        return _to_provider_profile_response(profile)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.delete(
    "/provider-profiles/{profile_id}",
    response_model=DeleteProviderProfileResponse,
)
def delete_provider_profile(
    profile_id: UUID,
    current_user: User = Depends(
        get_current_user,
    ),
    service: LLMProviderService = Depends(
        get_llm_provider_service,
    ),
):
    try:
        service.delete_profile(
            profile_id=profile_id,
            user_id=current_user.id,
        )

        return {
            "message": "LLM provider profile deleted successfully."
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.post(
    "/provider-profiles/{profile_id}/activate",
    response_model=ActivateProviderProfileResponse,
)
def activate_provider_profile(
    profile_id: UUID,
    current_user: User = Depends(
        get_current_user,
    ),
    service: LLMProviderService = Depends(
        get_llm_provider_service,
    ),
):
    try:
        profile = service.activate_profile(
            profile_id=profile_id,
            user_id=current_user.id,
        )

        return {
            "message": "LLM provider profile activated successfully.",
            "profile": _to_provider_profile_response(profile),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.post(
    "/provider-profiles/{profile_id}/test",
    response_model=ProviderConnectionTestResponse,
)
def test_provider_profile(
    profile_id: UUID,
    current_user: User = Depends(
        get_current_user,
    ),
    service: LLMProviderService = Depends(
        get_llm_provider_service,
    ),
):
    try:
        result = service.test_profile_connection(
            profile_id=profile_id,
            user_id=current_user.id,
        )

        return {
            "success": result.success,
            "message": result.message,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )
