import hmac
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

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
from growthos.models import BusinessLead, LandingPage
from growthos.rate_limit import public_quote_rate_limiter
from growthos.schemas_landing import (
    BusinessLeadCreate,
    BusinessLeadRead,
    BusinessLeadSummary,
    BusinessLeadUpdate,
    DemoLeadReceipt,
    DemoLeadRequest,
    LandingPageRead,
    LandingPageUpsert,
    PublicLandingRead,
)
from growthos.services import landing

router = APIRouter()


class LandingApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)


def enforce_public_rate_limit(slug: str, request: Request, settings: Settings) -> None:
    client_ip = str(getattr(request.state, "client_ip", "unknown"))
    limiter_key = (
        "landing:"
        + hmac.new(
            settings.auth_secret_key.encode(), f"{slug}:{client_ip}".encode(), sha256
        ).hexdigest()
    )
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


@router.get("/public/landing/{slug}", response_model=PublicLandingRead)
def read_public_landing(slug: str, session: Session = Depends(get_session)) -> PublicLandingRead:
    found = landing.get_public_landing(session, slug)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Página não encontrada")
    return landing.to_public(*found)


@router.post(
    "/public/landing/{slug}/demo-leads",
    response_model=DemoLeadReceipt,
    status_code=status.HTTP_202_ACCEPTED,
)
def receive_demo_lead(
    slug: str,
    payload: DemoLeadRequest,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> DemoLeadReceipt:
    found = landing.get_public_landing(session, slug)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Página não encontrada")
    enforce_public_rate_limit(slug, request, settings)
    try:
        lead = landing.create_demo_lead(session, found[0], payload)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return DemoLeadReceipt(
        reference=lead.id,
        message="Pedido demonstrativo registrado. Nenhum contato será feito.",
    )


@router.get("/businesses/{business_id}/landing-page", response_model=LandingPageRead)
def read_landing(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> LandingPage:
    require_capability(context, Capability.BUSINESS_LEAD_VIEW)
    business = get_scoped_business(session, context, business_id)
    page = landing.get_landing(session, business.id)
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Página ainda não criada")
    return page


@router.put("/businesses/{business_id}/landing-page", response_model=LandingPageRead)
def save_landing(
    business_id: UUID,
    payload: LandingPageUpsert,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> LandingPage:
    require_capability(context, Capability.SALES_LEAD_MANAGE)
    business = get_scoped_business(session, context, business_id)
    try:
        return landing.upsert_landing(session, context, business, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/businesses/{business_id}/landing-page/approve", response_model=LandingPageRead)
def approve_landing(
    business_id: UUID,
    payload: LandingApproval,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> LandingPage:
    require_capability(context, Capability.SALES_LEAD_MANAGE)
    business = get_scoped_business(session, context, business_id)
    page = landing.get_landing(session, business.id)
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Página ainda não criada")
    try:
        return landing.approve_landing(session, context, page, payload.version)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/businesses/{business_id}/landing-page/revoke", response_model=LandingPageRead)
def revoke_landing(
    business_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> LandingPage:
    require_capability(context, Capability.SALES_LEAD_MANAGE)
    business = get_scoped_business(session, context, business_id)
    page = landing.get_landing(session, business.id)
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Página ainda não criada")
    return landing.revoke_landing(session, context, page)


@router.get("/businesses/{business_id}/leads", response_model=list[BusinessLeadRead])
def list_business_leads(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[BusinessLead]:
    require_capability(context, Capability.BUSINESS_LEAD_VIEW)
    business = get_scoped_business(session, context, business_id)
    return landing.list_leads(session, business.id)


@router.get("/businesses/{business_id}/leads/summary", response_model=BusinessLeadSummary)
def summarize_business_leads(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> BusinessLeadSummary:
    require_capability(context, Capability.BUSINESS_LEAD_VIEW)
    business = get_scoped_business(session, context, business_id)
    return landing.summarize(session, business.id)


@router.post(
    "/businesses/{business_id}/leads",
    response_model=BusinessLeadRead,
    status_code=status.HTTP_201_CREATED,
)
def create_business_lead(
    business_id: UUID,
    payload: BusinessLeadCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> BusinessLead:
    require_capability(context, Capability.BUSINESS_LEAD_MANAGE)
    business = get_scoped_business(session, context, business_id)
    try:
        return landing.create_manual_lead(session, context, business, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.patch("/business-leads/{lead_id}", response_model=BusinessLeadRead)
def update_business_lead(
    lead_id: UUID,
    payload: BusinessLeadUpdate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> BusinessLead:
    require_capability(context, Capability.BUSINESS_LEAD_MANAGE)
    lead = landing.get_lead(session, context.organization.id, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interessado não encontrado")
    get_scoped_business(session, context, lead.business_id)
    try:
        return landing.update_lead(session, context, lead, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
