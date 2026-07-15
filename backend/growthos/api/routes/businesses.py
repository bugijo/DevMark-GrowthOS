from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    get_scoped_business,
    require_csrf,
    require_role,
)
from growthos.domain.enums import Role
from growthos.models import BrandProfile, Business, Membership, User
from growthos.schemas import (
    BrandProfileRead,
    BrandProfileUpsert,
    BusinessCreate,
    BusinessRead,
    BusinessUpdate,
    ReviewerCreate,
    ReviewerRead,
)
from growthos.security import hash_password, normalize_email
from growthos.services.audit import add_audit_log

router = APIRouter()

_AGENCY_WRITERS = (Role.SUPER_ADMIN, Role.AGENCY_ADMIN)
_BRAND_NOTES_INTERNAL_ONLY = frozenset({Role.CLIENT_OWNER, Role.CLIENT_REVIEWER, Role.VIEWER})


def _serialize_brand_profile(
    profile: BrandProfile,
    context: AuthContext,
) -> BrandProfileRead:
    result = BrandProfileRead.model_validate(profile)
    if context.membership.role in _BRAND_NOTES_INTERNAL_ONLY:
        return result.model_copy(update={"internal_notes": ""})
    return result


@router.get("", response_model=list[BusinessRead])
def list_businesses(
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[Business]:
    query = select(Business).where(
        Business.organization_id == context.organization.id,
        Business.is_active.is_(True),
    )
    if context.membership.business_id is not None:
        query = query.where(Business.id == context.membership.business_id)
    return list(session.scalars(query.order_by(Business.name)).all())


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
def create_business(
    payload: BusinessCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> Business:
    require_role(context, *_AGENCY_WRITERS)
    business = Business(
        organization_id=context.organization.id,
        name=payload.name.strip(),
        segment=payload.segment.strip(),
    )
    session.add(business)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um cliente com este nome") from exc
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="business.created",
        resource_type="business",
        resource_id=business.id,
        details={"name": business.name},
    )
    session.commit()
    return business


@router.get("/{business_id}", response_model=BusinessRead)
def get_business(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> Business:
    return get_scoped_business(session, context, business_id)


@router.post(
    "/{business_id}/reviewers",
    response_model=ReviewerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_reviewer(
    business_id: UUID,
    payload: ReviewerCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ReviewerRead:
    """Cria acesso local provisório; convites de uso único substituirão este fluxo."""
    require_role(context, *_AGENCY_WRITERS)
    business = get_scoped_business(session, context, business_id)
    email = normalize_email(payload.email)
    if session.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado")
    user = User(
        email=email,
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    session.add(user)
    session.flush()
    membership = Membership(
        organization_id=context.organization.id,
        user_id=user.id,
        role=Role.CLIENT_REVIEWER,
        business_id=business.id,
    )
    session.add(membership)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Revisor já possui vínculo") from exc
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="membership.client_reviewer_created",
        resource_type="membership",
        resource_id=membership.id,
        details={"user_id": str(user.id), "role": Role.CLIENT_REVIEWER.value},
    )
    session.commit()
    return ReviewerRead(user=user, membership=membership)


@router.patch("/{business_id}", response_model=BusinessRead)
def update_business(
    business_id: UUID,
    payload: BusinessUpdate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> Business:
    require_role(context, *_AGENCY_WRITERS)
    business = get_scoped_business(session, context, business_id)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        business.name = changes["name"].strip()
    if "segment" in changes:
        business.segment = changes["segment"].strip()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="business.updated",
        resource_type="business",
        resource_id=business.id,
        details={"fields": sorted(changes)},
    )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um cliente com este nome") from exc
    return business


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_business(
    business_id: UUID,
    response: Response,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> None:
    del response
    require_role(context, *_AGENCY_WRITERS)
    business = get_scoped_business(session, context, business_id)
    business.is_active = False
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="business.archived",
        resource_type="business",
        resource_id=business.id,
    )
    session.commit()


@router.get("/{business_id}/brand-profile", response_model=BrandProfileRead)
def get_brand_profile(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> BrandProfileRead:
    business = get_scoped_business(session, context, business_id)
    profile = session.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == context.organization.id,
            BrandProfile.business_id == business.id,
        )
    )
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand Kit ainda não cadastrado")
    return _serialize_brand_profile(profile, context)


@router.put("/{business_id}/brand-profile", response_model=BrandProfileRead)
def upsert_brand_profile(
    business_id: UUID,
    payload: BrandProfileUpsert,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> BrandProfile:
    require_role(context, *_AGENCY_WRITERS)
    business = get_scoped_business(session, context, business_id)
    profile = session.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == context.organization.id,
            BrandProfile.business_id == business.id,
        )
    )
    created = profile is None
    if profile is None:
        profile = BrandProfile(
            organization_id=context.organization.id,
            business_id=business.id,
            brand_name=payload.brand_name,
        )
        session.add(profile)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    session.flush()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="brand_profile.created" if created else "brand_profile.updated",
        resource_type="brand_profile",
        resource_id=profile.id,
        details={"fields": sorted(payload.model_fields_set or payload.model_fields)},
    )
    session.commit()
    session.refresh(profile)
    return profile
