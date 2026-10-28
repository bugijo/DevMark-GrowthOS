"""Landing pages por negócio cliente e acompanhamento dos interessados.

Regras de segurança do piloto:
- a página só é servida publicamente depois de aprovação humana explícita;
- qualquer edição de uma página aprovada a devolve para rascunho;
- o formulário público é demonstrativo: aceita apenas escolhas fechadas, grava
  `is_demo=True` e nunca dispara mensagem, e-mail ou publicação.
"""

from collections import Counter
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext
from growthos.models import Business, BusinessLead, LandingPage
from growthos.schemas_landing import (
    BusinessLeadCreate,
    BusinessLeadStatus,
    BusinessLeadSummary,
    BusinessLeadUpdate,
    DemoLeadRequest,
    LandingPageUpsert,
    LandingStatus,
    LeadSource,
    PublicLandingRead,
)
from growthos.services.audit import add_audit_log

_CLOSED_STATUSES = {
    BusinessLeadStatus.REALIZADO,
    BusinessLeadStatus.CANCELADO,
    BusinessLeadStatus.NAO_COMPARECEU,
}
_ALLOWED_TRANSITIONS: dict[BusinessLeadStatus, set[BusinessLeadStatus]] = {
    BusinessLeadStatus.NOVO: {
        BusinessLeadStatus.AGUARDANDO_DADOS,
        BusinessLeadStatus.HORARIO_OFERTADO,
        BusinessLeadStatus.CANCELADO,
    },
    BusinessLeadStatus.AGUARDANDO_DADOS: {
        BusinessLeadStatus.HORARIO_OFERTADO,
        BusinessLeadStatus.CANCELADO,
    },
    BusinessLeadStatus.HORARIO_OFERTADO: {
        BusinessLeadStatus.CONFIRMADO,
        BusinessLeadStatus.AGUARDANDO_DADOS,
        BusinessLeadStatus.CANCELADO,
    },
    BusinessLeadStatus.CONFIRMADO: {
        BusinessLeadStatus.REALIZADO,
        BusinessLeadStatus.NAO_COMPARECEU,
        BusinessLeadStatus.CANCELADO,
    },
    BusinessLeadStatus.REALIZADO: set(),
    BusinessLeadStatus.CANCELADO: set(),
    BusinessLeadStatus.NAO_COMPARECEU: set(),
}


def get_landing(session: Session, business_id: UUID) -> LandingPage | None:
    return session.scalar(select(LandingPage).where(LandingPage.business_id == business_id))


def upsert_landing(
    session: Session,
    context: AuthContext,
    business: Business,
    data: LandingPageUpsert,
) -> LandingPage:
    slug_owner = session.scalar(select(LandingPage).where(LandingPage.slug == data.slug))
    if slug_owner is not None and slug_owner.business_id != business.id:
        raise ValueError("Este endereço já está em uso por outra página")
    page = get_landing(session, business.id)
    values = data.model_dump()
    values["price_items"] = [item.model_dump() for item in data.price_items]
    if page is None:
        page = LandingPage(
            organization_id=business.organization_id,
            business_id=business.id,
            status=LandingStatus.DRAFT.value,
            demo_mode=True,
            version=1,
            **values,
        )
        session.add(page)
        action = "landing_page.created"
    else:
        for key, value in values.items():
            setattr(page, key, value)
        # Conteúdo alterado exige nova aprovação humana antes de voltar ao ar.
        page.status = LandingStatus.DRAFT.value
        page.approved_at = None
        page.approved_by_user_id = None
        page.version += 1
        action = "landing_page.updated"
    session.flush()
    add_audit_log(
        session,
        organization_id=business.organization_id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action=action,
        resource_type="landing_page",
        resource_id=page.id,
        details={"version": page.version, "status": page.status},
    )
    session.commit()
    session.refresh(page)
    return page


def approve_landing(
    session: Session, context: AuthContext, page: LandingPage, version: int
) -> LandingPage:
    if version != page.version:
        raise ValueError("A página mudou desde a revisão; revise a versão atual")
    page.status = LandingStatus.APPROVED.value
    page.approved_by_user_id = context.user.id
    page.approved_at = datetime.now(UTC)
    add_audit_log(
        session,
        organization_id=page.organization_id,
        business_id=page.business_id,
        actor_user_id=context.user.id,
        action="landing_page.approved",
        resource_type="landing_page",
        resource_id=page.id,
        details={"version": page.version},
    )
    session.commit()
    session.refresh(page)
    return page


def revoke_landing(session: Session, context: AuthContext, page: LandingPage) -> LandingPage:
    """Tira a página do ar imediatamente, mantendo o conteúdo como rascunho."""
    if page.status != LandingStatus.APPROVED.value:
        return page
    page.status = LandingStatus.DRAFT.value
    page.approved_at = None
    page.approved_by_user_id = None
    add_audit_log(
        session,
        organization_id=page.organization_id,
        business_id=page.business_id,
        actor_user_id=context.user.id,
        action="landing_page.revoked",
        resource_type="landing_page",
        resource_id=page.id,
        details={"version": page.version},
    )
    session.commit()
    session.refresh(page)
    return page


def get_public_landing(session: Session, slug: str) -> tuple[LandingPage, Business] | None:
    row = session.execute(
        select(LandingPage, Business)
        .join(Business, Business.id == LandingPage.business_id)
        .where(
            LandingPage.slug == slug,
            LandingPage.status == LandingStatus.APPROVED.value,
            Business.is_active.is_(True),
        )
    ).first()
    return None if row is None else (row[0], row[1])


def to_public(page: LandingPage, business: Business) -> PublicLandingRead:
    return PublicLandingRead.model_validate(
        {
            **{
                key: getattr(page, key)
                for key in PublicLandingRead.model_fields
                if key != "business_name"
            },
            "business_name": business.name,
        }
    )


def _price_for(page: LandingPage | None, label: str) -> tuple[str, int | None]:
    if page is None or not label:
        return "", None
    for item in page.price_items:
        if str(item.get("label", "")).casefold() == label.casefold():
            return str(item["label"]), item.get("price_cents")
    raise ValueError("Opção de porte inválida")


def create_demo_lead(session: Session, page: LandingPage, data: DemoLeadRequest) -> BusinessLead:
    if not page.demo_mode:
        raise PermissionError("Captação real ainda não liberada para esta página")
    if data.service_requested not in page.service_options:
        raise ValueError("Serviço inválido")
    label, price = _price_for(page, data.price_item_label)
    lead = BusinessLead(
        organization_id=page.organization_id,
        business_id=page.business_id,
        landing_page_id=page.id,
        source=LeadSource.LANDING_DEMO.value,
        status=BusinessLeadStatus.NOVO.value,
        is_demo=True,
        service_requested=data.service_requested,
        price_item_label=label,
        reference_price_cents=price,
        preferred_period=data.preferred_period,
        notes=f"Origem informada: {data.heard_from}",
        next_action="Confirmar disponibilidade e preço vigente com a equipe",
    )
    session.add(lead)
    session.flush()
    add_audit_log(
        session,
        organization_id=page.organization_id,
        business_id=page.business_id,
        actor_user_id=None,
        action="business_lead.demo_created",
        resource_type="business_lead",
        resource_id=lead.id,
        details={"source": lead.source, "is_demo": True},
    )
    session.commit()
    session.refresh(lead)
    return lead


def create_manual_lead(
    session: Session, context: AuthContext, business: Business, data: BusinessLeadCreate
) -> BusinessLead:
    page = get_landing(session, business.id)
    label, price = _price_for(page, data.price_item_label)
    lead = BusinessLead(
        organization_id=business.organization_id,
        business_id=business.id,
        landing_page_id=page.id if page else None,
        source=data.source.value,
        status=BusinessLeadStatus.NOVO.value,
        # Enquanto o gate de privacidade não for aprovado, todo registro é demonstrativo.
        is_demo=True,
        service_requested=data.service_requested,
        price_item_label=label,
        reference_price_cents=price,
        preferred_period=data.preferred_period,
        notes=data.notes,
    )
    session.add(lead)
    session.flush()
    add_audit_log(
        session,
        organization_id=business.organization_id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="business_lead.created",
        resource_type="business_lead",
        resource_id=lead.id,
        details={"source": lead.source, "is_demo": True},
    )
    session.commit()
    session.refresh(lead)
    return lead


def list_leads(session: Session, business_id: UUID) -> list[BusinessLead]:
    return list(
        session.scalars(
            select(BusinessLead)
            .where(BusinessLead.business_id == business_id)
            .order_by(BusinessLead.created_at.desc())
        )
    )


def get_lead(session: Session, organization_id: UUID, lead_id: UUID) -> BusinessLead | None:
    return session.scalar(
        select(BusinessLead).where(
            BusinessLead.id == lead_id, BusinessLead.organization_id == organization_id
        )
    )


def update_lead(
    session: Session, context: AuthContext, lead: BusinessLead, data: BusinessLeadUpdate
) -> BusinessLead:
    changes: dict[str, str] = {}
    if data.status is not None and data.status.value != lead.status:
        current = BusinessLeadStatus(lead.status)
        if data.status not in _ALLOWED_TRANSITIONS[current]:
            raise ValueError(f"Transição inválida: {current.value} → {data.status.value}")
        changes["status"] = f"{current.value}->{data.status.value}"
        lead.status = data.status.value
    if data.notes is not None:
        lead.notes = data.notes
        changes["notes"] = "updated"
    if data.next_action is not None:
        lead.next_action = data.next_action
        changes["next_action"] = "updated"
    if "next_action_due_at" in data.model_fields_set:
        lead.next_action_due_at = data.next_action_due_at
        changes["next_action_due_at"] = "updated"
    if not changes:
        return lead
    add_audit_log(
        session,
        organization_id=lead.organization_id,
        business_id=lead.business_id,
        actor_user_id=context.user.id,
        action="business_lead.updated",
        resource_type="business_lead",
        resource_id=lead.id,
        details=changes,
    )
    session.commit()
    session.refresh(lead)
    return lead


def summarize(session: Session, business_id: UUID) -> BusinessLeadSummary:
    leads = list_leads(session, business_id)
    now = datetime.now(UTC)
    open_leads = [lead for lead in leads if BusinessLeadStatus(lead.status) not in _CLOSED_STATUSES]
    page = get_landing(session, business_id)

    def _overdue(lead: BusinessLead) -> bool:
        due = lead.next_action_due_at
        if due is None:
            return False
        if due.tzinfo is None:
            due = due.replace(tzinfo=UTC)
        return due < now

    return BusinessLeadSummary(
        business_id=business_id,
        total=len(leads),
        demo=sum(1 for lead in leads if lead.is_demo),
        by_status=dict(Counter(lead.status for lead in leads)),
        by_source=dict(Counter(lead.source for lead in leads)),
        open_without_next_action=sum(1 for lead in open_leads if not lead.next_action),
        overdue_next_actions=sum(1 for lead in open_leads if _overdue(lead)),
        landing_status=LandingStatus(page.status) if page else None,
    )
