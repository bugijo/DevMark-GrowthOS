"""Privacidade, horários e pedidos reais dos interessados de um estabelecimento.

Regras:
- o estabelecimento (controlador) aprova o próprio aviso; a agência só redige;
- aprovar o aviso NÃO declara conformidade legal — exige reconhecer que a
  revisão jurídica é separada;
- pedidos reais só entram com três portões abertos: configuração global
  `public_lead_collection_enabled` (desligada por padrão, com revisões jurídica e de
  segurança declaradas), aviso aprovado e página fora do modo demonstração;
- dados de contato nunca vão para a trilha de auditoria;
- nada aqui envia mensagens: a resposta ao tutor continua sendo humana.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from growthos.config import Settings
from growthos.dependencies import AuthContext
from growthos.models import (
    AuditLog,
    Business,
    BusinessAvailability,
    BusinessLead,
    LandingPage,
    LeadPrivacySettings,
)
from growthos.schemas_landing import BusinessLeadRead, BusinessLeadStatus, LeadSource
from growthos.schemas_lead_privacy import (
    AvailabilityRead,
    AvailabilityUpsert,
    LeadExport,
    LeadPrivacyUpsert,
    LeadRetentionResult,
    PublicAvailabilityDay,
    PublicPrivacyNotice,
    RealLeadRequest,
)
from growthos.services.audit import add_audit_log
from growthos.services.landing import _price_for

DUPLICATE_WINDOW = timedelta(hours=24)
WEEKDAY_NAMES = (
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
)


def _actor(context: AuthContext | None) -> UUID | None:
    return context.user.id if context is not None else None


# --- Aviso de privacidade -------------------------------------------------


def get_privacy(session: Session, business_id: UUID) -> LeadPrivacySettings | None:
    return session.scalar(
        select(LeadPrivacySettings).where(LeadPrivacySettings.business_id == business_id)
    )


def upsert_privacy(
    session: Session, context: AuthContext, business: Business, data: LeadPrivacyUpsert
) -> LeadPrivacySettings:
    row = get_privacy(session, business.id)
    values = data.model_dump()
    if row is None:
        row = LeadPrivacySettings(
            organization_id=business.organization_id, business_id=business.id, **values
        )
        session.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
        row.version += 1
    row.status = "DRAFT"
    row.approved_by_user_id = None
    row.approved_at = None
    row.approval_note = ""
    session.flush()
    add_audit_log(
        session,
        organization_id=business.organization_id,
        business_id=business.id,
        actor_user_id=_actor(context),
        action="lead_privacy.saved",
        resource_type="lead_privacy_settings",
        resource_id=row.id,
        details={
            "version": row.version,
            "legal_basis": row.legal_basis,
            "retention_days": row.retention_days,
        },
    )
    session.commit()
    session.refresh(row)
    return row


def approve_privacy(
    session: Session, context: AuthContext, row: LeadPrivacySettings, version: int, note: str
) -> LeadPrivacySettings:
    if row.version != version:
        raise ValueError("O aviso mudou desde que foi revisado; revise a versão atual")
    if row.status == "APPROVED":
        raise ValueError("Esta versão já está aprovada")
    row.status = "APPROVED"
    row.approved_by_user_id = context.user.id
    row.approved_at = datetime.now(UTC)
    row.approval_note = note
    add_audit_log(
        session,
        organization_id=row.organization_id,
        business_id=row.business_id,
        actor_user_id=context.user.id,
        action="lead_privacy.approved",
        resource_type="lead_privacy_settings",
        resource_id=row.id,
        details={"version": row.version, "acknowledged_not_legal_advice": True},
    )
    session.commit()
    session.refresh(row)
    return row


def public_notice(row: LeadPrivacySettings | None) -> PublicPrivacyNotice | None:
    if row is None or row.status != "APPROVED":
        return None
    return PublicPrivacyNotice(
        controller_name=row.controller_name,
        privacy_contact=row.privacy_contact,
        purpose=row.purpose,
        legal_basis=row.legal_basis,
        data_categories=row.data_categories,
        retention_days=row.retention_days,
        notice_text=row.notice_text,
        version=row.version,
    )


def collection_blocker(
    settings: Settings, page: LandingPage, privacy: LeadPrivacySettings | None
) -> str | None:
    """Motivo pelo qual pedidos reais estão bloqueados, ou None se liberados."""

    if not settings.public_lead_collection_enabled:
        return "Coleta de pedidos reais desligada neste ambiente"
    if privacy is None or privacy.status != "APPROVED":
        return "Aviso de privacidade do estabelecimento ainda não aprovado"
    if page.demo_mode:
        return "A página ainda está em modo demonstração"
    return None


# --- Horários ---------------------------------------------------------------


def get_availability(session: Session, business_id: UUID) -> AvailabilityRead:
    row = session.scalar(
        select(BusinessAvailability).where(BusinessAvailability.business_id == business_id)
    )
    if row is None:
        return AvailabilityRead(
            business_id=business_id,
            slots=[],
            notes="",
            confirmed_by_business=False,
            version=0,
            updated_at=None,
        )
    return AvailabilityRead.model_validate(row)


def upsert_availability(
    session: Session, context: AuthContext, business: Business, data: AvailabilityUpsert
) -> AvailabilityRead:
    row = session.scalar(
        select(BusinessAvailability).where(BusinessAvailability.business_id == business.id)
    )
    slots = [slot.model_dump() for slot in data.slots]
    if row is None:
        row = BusinessAvailability(
            organization_id=business.organization_id,
            business_id=business.id,
            slots=slots,
            notes=data.notes,
            confirmed_by_business=data.confirmed_by_business,
            updated_by_user_id=context.user.id,
        )
        session.add(row)
    else:
        row.slots = slots
        row.notes = data.notes
        row.confirmed_by_business = data.confirmed_by_business
        row.updated_by_user_id = context.user.id
        row.version += 1
    session.flush()
    add_audit_log(
        session,
        organization_id=business.organization_id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="business_availability.saved",
        resource_type="business_availability",
        resource_id=row.id,
        details={
            "version": row.version,
            "slots": len(slots),
            "confirmed_by_business": row.confirmed_by_business,
        },
    )
    session.commit()
    session.refresh(row)
    return AvailabilityRead.model_validate(row)


def public_availability(session: Session, business_id: UUID) -> list[PublicAvailabilityDay]:
    """Dias e períodos oferecidos no formulário — só o que o estabelecimento confirmou."""

    availability = get_availability(session, business_id)
    if not availability.confirmed_by_business:
        return []
    periods: dict[int, set[str]] = {}
    for slot in availability.slots:
        day = periods.setdefault(slot.weekday, set())
        if slot.start < "12:00":
            day.add("Manhã")
        if slot.end > "12:00":
            day.add("Tarde")
    return [
        PublicAvailabilityDay(
            weekday=weekday,
            periods=[p for p in ("Manhã", "Tarde") if p in periods[weekday]],
        )
        for weekday in sorted(periods)
    ]


def resolve_preference(
    session: Session, business_id: UUID, weekday: int | None, period: str
) -> str:
    """Texto do dia/período pedido; recusa dia ou período fora dos horários confirmados.

    É só uma preferência do tutor: a equipe ainda confirma o horário manualmente.
    """

    if weekday is None:
        return period
    offered = {day.weekday: day.periods for day in public_availability(session, business_id)}
    if weekday not in offered or (period != "Sem preferência" and period not in offered[weekday]):
        raise ValueError("Dia ou período fora dos horários informados pelo estabelecimento")
    return f"{WEEKDAY_NAMES[weekday]} · {period}"


# --- Pedido real ------------------------------------------------------------


def create_real_lead(
    session: Session,
    page: LandingPage,
    privacy: LeadPrivacySettings,
    data: RealLeadRequest,
) -> BusinessLead:
    if not data.privacy_accepted:
        raise ValueError("É preciso aceitar o aviso de privacidade")
    if data.privacy_notice_version != privacy.version:
        raise ValueError("O aviso de privacidade mudou; recarregue a página")
    if data.service_requested not in page.service_options:
        raise ValueError("Serviço inválido")
    period = resolve_preference(
        session, page.business_id, data.preferred_weekday, data.preferred_period
    )
    now = datetime.now(UTC)
    duplicate = session.scalar(
        select(BusinessLead).where(
            BusinessLead.business_id == page.business_id,
            BusinessLead.contact_phone == data.contact_phone,
            BusinessLead.anonymized_at.is_(None),
            BusinessLead.created_at >= now - DUPLICATE_WINDOW,
        )
    )
    if duplicate is not None:
        return duplicate
    label, price = _price_for(page, data.price_item_label)
    lead = BusinessLead(
        organization_id=page.organization_id,
        business_id=page.business_id,
        landing_page_id=page.id,
        source=LeadSource.LANDING_PAGE.value,
        status=BusinessLeadStatus.NOVO.value,
        is_demo=False,
        service_requested=data.service_requested,
        price_item_label=label,
        reference_price_cents=price,
        preferred_period=period,
        notes=f"Origem informada: {data.heard_from}",
        next_action="Responder ao tutor e confirmar horário e preço vigente",
        contact_name=data.contact_name,
        contact_phone=data.contact_phone,
        privacy_notice_version=privacy.version,
        consent_recorded_at=now,
    )
    session.add(lead)
    session.flush()
    add_audit_log(
        session,
        organization_id=page.organization_id,
        business_id=page.business_id,
        actor_user_id=None,
        action="business_lead.received",
        resource_type="business_lead",
        resource_id=lead.id,
        details={"source": lead.source, "privacy_notice_version": privacy.version},
    )
    session.commit()
    session.refresh(lead)
    return lead


def record_spam_drop(session: Session, page: LandingPage) -> None:
    add_audit_log(
        session,
        organization_id=page.organization_id,
        business_id=page.business_id,
        actor_user_id=None,
        action="business_lead.spam_dropped",
        resource_type="landing_page",
        resource_id=page.id,
        details={"reason": "honeypot"},
    )
    session.commit()


# --- Direitos do titular e retenção ----------------------------------------


def export_lead(
    session: Session, context: AuthContext, lead: BusinessLead, business: Business
) -> LeadExport:
    history = session.scalars(
        select(AuditLog)
        .where(
            AuditLog.organization_id == lead.organization_id,
            AuditLog.resource_type == "business_lead",
            AuditLog.resource_id == lead.id,
        )
        .order_by(AuditLog.created_at)
    ).all()
    privacy = get_privacy(session, lead.business_id)
    add_audit_log(
        session,
        organization_id=lead.organization_id,
        business_id=lead.business_id,
        actor_user_id=context.user.id,
        action="business_lead.exported",
        resource_type="business_lead",
        resource_id=lead.id,
        details={},
    )
    session.commit()
    return LeadExport(
        exported_at=datetime.now(UTC),
        business_name=business.name,
        controller_name=privacy.controller_name if privacy else None,
        lead=BusinessLeadRead.model_validate(lead),
        history=[{"action": entry.action, "at": entry.created_at.isoformat()} for entry in history],
    )


def _wipe(lead: BusinessLead, now: datetime) -> None:
    lead.contact_name = None
    lead.contact_phone = None
    lead.notes = ""
    lead.next_action = ""
    lead.next_action_due_at = None
    lead.anonymized_at = now


def anonymize_lead(
    session: Session, context: AuthContext | None, lead: BusinessLead, *, reason: str
) -> BusinessLead:
    if lead.anonymized_at is not None:
        return lead
    _wipe(lead, datetime.now(UTC))
    add_audit_log(
        session,
        organization_id=lead.organization_id,
        business_id=lead.business_id,
        actor_user_id=_actor(context),
        action="business_lead.anonymized",
        resource_type="business_lead",
        resource_id=lead.id,
        details={"reason": reason},
    )
    session.commit()
    session.refresh(lead)
    return lead


def run_retention(
    session: Session, context: AuthContext | None, business: Business, *, dry_run: bool
) -> LeadRetentionResult:
    privacy = get_privacy(session, business.id)
    if privacy is None:
        raise ValueError("Configure a política de retenção no aviso de privacidade")
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=privacy.retention_days)
    candidates = session.scalars(
        select(BusinessLead).where(
            BusinessLead.business_id == business.id,
            BusinessLead.anonymized_at.is_(None),
            BusinessLead.created_at < cutoff,
            or_(
                BusinessLead.contact_name.is_not(None),
                BusinessLead.contact_phone.is_not(None),
                BusinessLead.notes != "",
            ),
        )
    ).all()
    if not dry_run:
        for lead in candidates:
            _wipe(lead, now)
    details: dict[str, Any] = {
        "retention_days": privacy.retention_days,
        "eligible": len(candidates),
        "dry_run": dry_run,
    }
    add_audit_log(
        session,
        organization_id=business.organization_id,
        business_id=business.id,
        actor_user_id=_actor(context),
        action="business_lead.retention_run",
        resource_type="lead_privacy_settings",
        resource_id=privacy.id,
        details=details,
    )
    session.commit()
    return LeadRetentionResult(
        business_id=business.id,
        retention_days=privacy.retention_days,
        cutoff=cutoff,
        eligible=len(candidates),
        anonymized=0 if dry_run else len(candidates),
        dry_run=dry_run,
    )
