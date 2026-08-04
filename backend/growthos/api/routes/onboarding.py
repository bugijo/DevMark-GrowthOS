from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    get_scoped_business,
    require_capability,
    require_csrf,
)
from growthos.domain.enums import Role
from growthos.domain.permissions import Capability
from growthos.models import Membership, User
from growthos.schemas_onboarding import (
    BusinessOnboardingRead,
    OnboardingApproverRead,
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


@router.get(
    "/businesses/{business_id}/onboarding/approvers",
    response_model=list[OnboardingApproverRead],
)
def list_business_onboarding_approvers(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[OnboardingApproverRead]:
    """Expõe somente aprovadores ativos do cliente para o assistente."""

    require_capability(context, Capability.ONBOARDING_VIEW)
    business = get_scoped_business(session, context, business_id)
    rows = session.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.organization_id == context.organization.id,
            Membership.business_id == business.id,
            Membership.role.in_((Role.CLIENT_OWNER, Role.CLIENT_REVIEWER)),
            Membership.is_active.is_(True),
            User.is_active.is_(True),
        )
        .order_by(User.name, User.email, Membership.id)
    ).all()
    return [
        OnboardingApproverRead(
            membership_id=membership.id,
            user_id=user.id,
            business_id=business.id,
            name=user.name,
            email=user.email,
            role=membership.role,
        )
        for membership, user in rows
    ]


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
