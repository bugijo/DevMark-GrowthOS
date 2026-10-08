import hmac
import re
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.config import Settings, get_settings
from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    require_capability,
    require_csrf,
)
from growthos.domain.permissions import Capability
from growthos.models import Organization, SalesLead, SalesLeadTask
from growthos.rate_limit import public_quote_rate_limiter
from growthos.schemas_sales import (
    LeadBriefingRead,
    LeadStage,
    LeadStageUpdate,
    LeadTaskCreate,
    LeadTaskRead,
    ManualLeadCreate,
    ProposalDraftRead,
    PublicQuoteConfig,
    PublicQuoteReceipt,
    PublicQuoteRequest,
    SalesLeadRead,
)
from growthos.services import sales

router = APIRouter()
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9._:-]{16,100}$")


@router.get("/public/quote-requests/config", response_model=PublicQuoteConfig)
def public_quote_config(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PublicQuoteConfig:
    organization = _public_target(session, settings)
    if not settings.public_quote_intake_enabled or organization is None:
        return PublicQuoteConfig(enabled=False)
    return PublicQuoteConfig(
        enabled=True,
        privacy_notice_url=settings.public_quote_privacy_notice_url,
        privacy_notice_version=settings.public_quote_privacy_notice_version,
    )


@router.post(
    "/public/quote-requests",
    response_model=PublicQuoteReceipt,
    status_code=status.HTTP_202_ACCEPTED,
)
def receive_public_quote(
    payload: PublicQuoteRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PublicQuoteReceipt:
    if not settings.public_quote_intake_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Formulário indisponível")
    organization = _public_target(session, settings)
    if organization is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Destino do formulário indisponível"
        )
    if not idempotency_key or not _IDEMPOTENCY_KEY.fullmatch(idempotency_key):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Identificador de envio inválido")

    client_ip = str(getattr(request.state, "client_ip", "unknown"))
    limiter_key = hmac.new(
        settings.auth_secret_key.encode(), client_ip.encode(), sha256
    ).hexdigest()
    retry_after = public_quote_rate_limiter.allow(
        limiter_key,
        limit=settings.public_quote_rate_limit_attempts,
        window_seconds=settings.public_quote_rate_limit_window_seconds,
    )
    if retry_after is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Tente novamente mais tarde",
            headers={"Retry-After": str(retry_after)},
        )

    if payload.honeypot:
        # Bots receive the same generic receipt, but their content is not persisted.
        return PublicQuoteReceipt(reference=uuid4())
    lead = sales.create_public_lead(
        session,
        organization_id=organization.id,
        data=payload,
        idempotency_key=idempotency_key,
        privacy_notice_version=settings.public_quote_privacy_notice_version,
    )
    return PublicQuoteReceipt(reference=lead.id)


@router.get("/sales/leads", response_model=list[SalesLeadRead])
def list_sales_leads(
    stage: LeadStage | None = Query(default=None),
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[SalesLead]:
    require_capability(context, Capability.SALES_LEAD_VIEW)
    return sales.list_leads(session, context.organization.id, stage)


@router.post("/sales/leads", response_model=SalesLeadRead, status_code=status.HTTP_201_CREATED)
def create_manual_sales_lead(
    payload: ManualLeadCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> SalesLead:
    require_capability(context, Capability.SALES_LEAD_MANAGE)
    return sales.create_manual_lead(session, context, payload)


@router.patch("/sales/leads/{lead_id}/stage", response_model=SalesLeadRead)
def change_sales_lead_stage(
    lead_id: UUID,
    payload: LeadStageUpdate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> SalesLead:
    require_capability(context, Capability.SALES_LEAD_MANAGE)
    lead = _scoped_lead(session, context, lead_id)
    try:
        return sales.update_stage(session, context, lead, payload.stage)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/sales/leads/{lead_id}/briefing", response_model=LeadBriefingRead)
def read_sales_lead_briefing(
    lead_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> LeadBriefingRead:
    require_capability(context, Capability.SALES_LEAD_VIEW)
    return sales.build_briefing(_scoped_lead(session, context, lead_id))


@router.post("/sales/leads/{lead_id}/proposal-draft", response_model=ProposalDraftRead)
def draft_sales_proposal(
    lead_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ProposalDraftRead:
    require_capability(context, Capability.SALES_LEAD_MANAGE)
    lead = _scoped_lead(session, context, lead_id)
    try:
        return sales.generate_proposal_draft(session, context, lead)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/sales/leads/{lead_id}/tasks", response_model=list[LeadTaskRead])
def list_sales_lead_tasks(
    lead_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[SalesLeadTask]:
    require_capability(context, Capability.SALES_LEAD_VIEW)
    _scoped_lead(session, context, lead_id)
    return sales.list_tasks(session, context.organization.id, lead_id)


@router.post(
    "/sales/leads/{lead_id}/tasks",
    response_model=LeadTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_sales_lead_task(
    lead_id: UUID,
    payload: LeadTaskCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> SalesLeadTask:
    require_capability(context, Capability.SALES_LEAD_MANAGE)
    lead = _scoped_lead(session, context, lead_id)
    return sales.create_task(session, context, lead, payload)


def _public_target(session: Session, settings: Settings) -> Organization | None:
    if not settings.public_quote_target_organization_slug:
        return None
    return session.scalar(
        select(Organization).where(
            Organization.slug == settings.public_quote_target_organization_slug
        )
    )


def _scoped_lead(session: Session, context: AuthContext, lead_id: UUID) -> SalesLead:
    lead = sales.get_lead(session, context.organization.id, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Oportunidade não encontrada")
    return lead
