"""API somente leitura para integrações de máquina (Hermes).

Autenticação por `Authorization: Bearer <token de integração>`, nunca por cookie
de sessão. Apenas GET; cada acesso gera `integration.read` na auditoria.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.models import Business
from growthos.schemas_landing import BusinessLeadStatus, BusinessLeadSummary, LeadSource
from growthos.services import integrations, landing

router = APIRouter(prefix="/integrations/v1")


class IntegrationBusiness(BaseModel):
    id: UUID
    name: str
    summary: BusinessLeadSummary


class IntegrationLead(BaseModel):
    """Campos de acompanhamento; observações livres ficam fora por mínimo privilégio."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source: LeadSource
    status: BusinessLeadStatus
    is_demo: bool
    service_requested: str
    price_item_label: str
    reference_price_cents: int | None
    preferred_period: str
    next_action: str
    next_action_due_at: datetime | None
    created_at: datetime
    updated_at: datetime


def require_leads_read(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> integrations.IntegrationContext:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Credencial de integração inválida",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise unauthorized
    context = integrations.authenticate(session, authorization[7:].strip())
    if context is None:
        raise unauthorized
    if integrations.LEADS_READ not in context.scopes:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Escopo insuficiente")
    return context


def _scoped_business(
    session: Session, context: integrations.IntegrationContext, business_id: UUID
) -> Business:
    business = session.scalar(
        select(Business).where(
            Business.id == business_id,
            Business.organization_id == context.organization_id,
            Business.is_active.is_(True),
        )
    )
    if business is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
    return business


@router.get("/businesses", response_model=list[IntegrationBusiness])
def list_businesses(
    context: integrations.IntegrationContext = Depends(require_leads_read),
    session: Session = Depends(get_session),
) -> list[IntegrationBusiness]:
    businesses = session.scalars(
        select(Business)
        .where(Business.organization_id == context.organization_id, Business.is_active.is_(True))
        .order_by(Business.name)
    ).all()
    result = [
        IntegrationBusiness(id=b.id, name=b.name, summary=landing.summarize(session, b.id))
        for b in businesses
    ]
    integrations.record_read(session, context, resource="businesses", business_id=None)
    return result


@router.get("/businesses/{business_id}/leads/summary", response_model=BusinessLeadSummary)
def read_summary(
    business_id: UUID,
    context: integrations.IntegrationContext = Depends(require_leads_read),
    session: Session = Depends(get_session),
) -> BusinessLeadSummary:
    business = _scoped_business(session, context, business_id)
    summary = landing.summarize(session, business.id)
    integrations.record_read(session, context, resource="leads.summary", business_id=business.id)
    return summary


@router.get("/businesses/{business_id}/leads", response_model=list[IntegrationLead])
def read_leads(
    business_id: UUID,
    context: integrations.IntegrationContext = Depends(require_leads_read),
    session: Session = Depends(get_session),
) -> list[IntegrationLead]:
    business = _scoped_business(session, context, business_id)
    leads = [
        IntegrationLead.model_validate(lead) for lead in landing.list_leads(session, business.id)
    ]
    integrations.record_read(session, context, resource="leads", business_id=business.id)
    return leads
