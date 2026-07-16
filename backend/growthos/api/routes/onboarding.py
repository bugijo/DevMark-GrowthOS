from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    get_scoped_business,
    require_capability,
    require_csrf,
)
from growthos.domain.permissions import Capability
from growthos.schemas_onboarding import (
    BusinessOnboardingRead,
    OnboardingCompleteRequest,
    OnboardingStepPayload,
)
from growthos.services.onboarding import (
    OnboardingConflictError,
    OnboardingNotFoundError,
    OnboardingResourceNotFoundError,
    OnboardingValidationError,
    complete_onboarding,
    read_onboarding,
    save_onboarding_step,
    start_onboarding,
)

router = APIRouter()


@router.post(
    "/businesses/{business_id}/onboarding",
    response_model=BusinessOnboardingRead,
)
def start_business_onboarding(
    business_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> BusinessOnboardingRead:
    require_capability(context, Capability.ONBOARDING_MANAGE)
    business = get_scoped_business(session, context, business_id)
    try:
        return start_onboarding(
            session,
            organization_id=context.organization.id,
            actor_user_id=context.user.id,
            business=business,
        )
    except OnboardingConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get(
    "/businesses/{business_id}/onboarding",
    response_model=BusinessOnboardingRead,
)
def get_business_onboarding(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> BusinessOnboardingRead:
    require_capability(context, Capability.ONBOARDING_VIEW)
    business = get_scoped_business(session, context, business_id)
    try:
        return read_onboarding(
            session,
            organization_id=context.organization.id,
            business=business,
        )
    except OnboardingNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.put(
    "/businesses/{business_id}/onboarding/steps/{step}",
    response_model=BusinessOnboardingRead,
)
def save_business_onboarding_step(
    business_id: UUID,
    payload: OnboardingStepPayload,
    step: int = Path(ge=1, le=15),
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> BusinessOnboardingRead:
    require_capability(context, Capability.ONBOARDING_MANAGE)
    if payload.step != step:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "A etapa do corpo deve corresponder à etapa da URL",
        )
    business = get_scoped_business(session, context, business_id)
    try:
        return save_onboarding_step(
            session,
            organization_id=context.organization.id,
            actor_user_id=context.user.id,
            business=business,
            payload=payload,
        )
    except OnboardingNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except OnboardingResourceNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except OnboardingValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except OnboardingConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post(
    "/businesses/{business_id}/onboarding/complete",
    response_model=BusinessOnboardingRead,
)
def complete_business_onboarding(
    business_id: UUID,
    payload: OnboardingCompleteRequest,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> BusinessOnboardingRead:
    require_capability(context, Capability.ONBOARDING_MANAGE)
    business = get_scoped_business(session, context, business_id)
    try:
        return complete_onboarding(
            session,
            organization_id=context.organization.id,
            actor_user_id=context.user.id,
            business=business,
            expected_revision=payload.revision,
        )
    except OnboardingNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except OnboardingConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
