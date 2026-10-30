"""API somente leitura para integrações de máquina (Hermes).

Autenticação por `Authorization: Bearer <token de integração>`, nunca por cookie
de sessão. Apenas GET; cada acesso gera `integration.read` na auditoria.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.domain.enums import ContentStatus
from growthos.models import Business, ContentItem
from growthos.schemas_landing import BusinessLeadStatus, BusinessLeadSummary, LeadSource
from growthos.services import integrations, landing

router = APIRouter(prefix="/integrations/v1")


class IntegrationPendingContents(BaseModel):
    """Somente contagens: o texto dos conteúdos não sai pela integração."""

    business_id: UUID
    by_status: dict[str, int]
    awaiting_client_decision: int
    oldest_waiting_since: datetime | None


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


def _authenticate(
    authorization: str | None, session: Session, scope: str
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
    if scope not in context.scopes:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Escopo insuficiente")
    return context


def require_leads_read(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> integrations.IntegrationContext:
    return _authenticate(authorization, session, integrations.LEADS_READ)


def require_contents_read(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> integrations.IntegrationContext:
    return _authenticate(authorization, session, integrations.CONTENTS_READ)


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


_PENDING_CONTENT = (
    ContentStatus.INTERNAL_REVIEW,
    ContentStatus.CLIENT_REVIEW,
    ContentStatus.CHANGES_REQUESTED,
)


@router.get("/businesses/{business_id}/contents/pending", response_model=IntegrationPendingContents)
def read_pending_contents(
    business_id: UUID,
    context: integrations.IntegrationContext = Depends(require_contents_read),
    session: Session = Depends(get_session),
) -> IntegrationPendingContents:
    business = _scoped_business(session, context, business_id)
    predicate = (
        ContentItem.organization_id == context.organization_id,
        ContentItem.business_id == business.id,
        ContentItem.status.in_(_PENDING_CONTENT),
    )
    rows = session.execute(
        select(ContentItem.status, func.count()).where(*predicate).group_by(ContentItem.status)
    ).all()
    by_status = {str(getattr(row[0], "value", row[0])): int(row[1]) for row in rows}
    oldest = session.scalar(
        select(func.min(ContentItem.updated_at)).where(
            *predicate[:2], ContentItem.status == ContentStatus.CLIENT_REVIEW
        )
    )
    integrations.record_read(session, context, resource="contents.pending", business_id=business.id)
    return IntegrationPendingContents(
        business_id=business.id,
        by_status=by_status,
        awaiting_client_decision=by_status.get(ContentStatus.CLIENT_REVIEW.value, 0),
        oldest_waiting_since=oldest,
    )
