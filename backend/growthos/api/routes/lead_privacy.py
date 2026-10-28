from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from growthos.api.routes.landing import enforce_public_rate_limit
from growthos.config import Settings, get_settings
from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    get_scoped_business,
    require_capability,
    require_csrf,
)
from growthos.domain.permissions import Capability
from growthos.models import BusinessLead, LeadPrivacySettings
from growthos.schemas_landing import BusinessLeadRead, DemoLeadReceipt
from growthos.schemas_lead_privacy import (
    AvailabilityRead,
    AvailabilityUpsert,
    LeadExport,
    LeadPrivacyApproval,
    LeadPrivacyRead,
    LeadPrivacyUpsert,
    LeadRetentionResult,
    LeadRetentionRun,
    PublicPrivacyNotice,
    RealLeadRequest,
)
from growthos.services import landing, lead_privacy

router = APIRouter()


class PublicIntakeRead(BaseModel):
    collection_open: bool
    notice: PublicPrivacyNotice | None


@router.get("/public/landing/{slug}/intake", response_model=PublicIntakeRead)
def read_public_intake(
    slug: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PublicIntakeRead:
    found = landing.get_public_landing(session, slug)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Página não encontrada")
    privacy = lead_privacy.get_privacy(session, found[0].business_id)
    return PublicIntakeRead(
        collection_open=lead_privacy.collection_blocker(settings, found[0], privacy) is None,
        notice=lead_privacy.public_notice(privacy),
    )


@router.post(
    "/public/landing/{slug}/requests",
    response_model=DemoLeadReceipt,
    status_code=status.HTTP_202_ACCEPTED,
)
def receive_real_lead(
    slug: str,
    payload: RealLeadRequest,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> DemoLeadReceipt:
    found = landing.get_public_landing(session, slug)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Página não encontrada")
    page = found[0]
    privacy = lead_privacy.get_privacy(session, page.business_id)
    blocker = lead_privacy.collection_blocker(settings, page, privacy)
    if blocker is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, blocker)
    enforce_public_rate_limit(slug, request, settings)
    receipt_message = "Pedido recebido. A equipe do estabelecimento vai responder."
    if payload.website:
        lead_privacy.record_spam_drop(session, page)
        return DemoLeadReceipt(reference=uuid4(), message=receipt_message)
    assert privacy is not None
    try:
        lead = lead_privacy.create_real_lead(session, page, privacy, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return DemoLeadReceipt(reference=lead.id, message=receipt_message)


def _privacy_or_404(session: Session, business_id: UUID) -> LeadPrivacySettings:
    row = lead_privacy.get_privacy(session, business_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aviso de privacidade ainda não criado")
    return row


@router.get("/businesses/{business_id}/lead-privacy", response_model=LeadPrivacyRead)
def read_lead_privacy(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> LeadPrivacySettings:
    require_capability(context, Capability.BUSINESS_LEAD_VIEW)
    business = get_scoped_business(session, context, business_id)
    return _privacy_or_404(session, business.id)


@router.put("/businesses/{business_id}/lead-privacy", response_model=LeadPrivacyRead)
def save_lead_privacy(
    business_id: UUID,
    payload: LeadPrivacyUpsert,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> LeadPrivacySettings:
    require_capability(context, Capability.LEAD_PRIVACY_CONFIGURE)
    business = get_scoped_business(session, context, business_id)
    return lead_privacy.upsert_privacy(session, context, business, payload)


@router.post("/businesses/{business_id}/lead-privacy/approve", response_model=LeadPrivacyRead)
def approve_lead_privacy(
    business_id: UUID,
    payload: LeadPrivacyApproval,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> LeadPrivacySettings:
    require_capability(context, Capability.LEAD_PRIVACY_APPROVE)
    business = get_scoped_business(session, context, business_id)
    row = _privacy_or_404(session, business.id)
    try:
        return lead_privacy.approve_privacy(session, context, row, payload.version, payload.note)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/businesses/{business_id}/availability", response_model=AvailabilityRead)
def read_availability(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> AvailabilityRead:
    require_capability(context, Capability.BUSINESS_LEAD_VIEW)
    business = get_scoped_business(session, context, business_id)
    return lead_privacy.get_availability(session, business.id)


@router.put("/businesses/{business_id}/availability", response_model=AvailabilityRead)
def save_availability(
    business_id: UUID,
    payload: AvailabilityUpsert,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> AvailabilityRead:
    require_capability(context, Capability.BUSINESS_AVAILABILITY_MANAGE)
    business = get_scoped_business(session, context, business_id)
    return lead_privacy.upsert_availability(session, context, business, payload)


def _scoped_lead(session: Session, context: AuthContext, lead_id: UUID) -> BusinessLead:
    require_capability(context, Capability.BUSINESS_LEAD_PRIVACY)
    lead = landing.get_lead(session, context.organization.id, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interessado não encontrado")
    get_scoped_business(session, context, lead.business_id)
    return lead


@router.get("/business-leads/{lead_id}/export", response_model=LeadExport)
def export_business_lead(
    lead_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> LeadExport:
    lead = _scoped_lead(session, context, lead_id)
    business = get_scoped_business(session, context, lead.business_id)
    return lead_privacy.export_lead(session, context, lead, business)


@router.post("/business-leads/{lead_id}/anonymize", response_model=BusinessLeadRead)
def anonymize_business_lead(
    lead_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> BusinessLead:
    lead = _scoped_lead(session, context, lead_id)
    return lead_privacy.anonymize_lead(session, context, lead, reason="pedido_do_titular")


@router.post("/businesses/{business_id}/leads/retention", response_model=LeadRetentionResult)
def run_lead_retention(
    business_id: UUID,
    payload: LeadRetentionRun,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> LeadRetentionResult:
    require_capability(context, Capability.BUSINESS_LEAD_PRIVACY)
    business = get_scoped_business(session, context, business_id)
    try:
        return lead_privacy.run_retention(session, context, business, dry_run=payload.dry_run)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
