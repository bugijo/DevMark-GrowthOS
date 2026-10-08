from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext
from growthos.models import SalesLead, SalesLeadTask
from growthos.schemas_sales import (
    LeadBriefingRead,
    LeadStage,
    LeadTaskCreate,
    ManualLeadCreate,
    ProposalDraftRead,
    PublicQuoteRequest,
    SalesInput,
    ServiceClassification,
)
from growthos.services.audit import add_audit_log

_NEXT_STAGE: dict[LeadStage, LeadStage | None] = {
    LeadStage.NEW_LEAD: LeadStage.CONTACT_PENDING,
    LeadStage.CONTACT_PENDING: LeadStage.BRIEFING,
    LeadStage.BRIEFING: LeadStage.PROPOSAL_PREPARATION,
    LeadStage.PROPOSAL_PREPARATION: LeadStage.PROPOSAL_SENT,
    LeadStage.PROPOSAL_SENT: LeadStage.NEGOTIATION,
    LeadStage.NEGOTIATION: LeadStage.CONTRACTED,
    LeadStage.CONTRACTED: LeadStage.IN_PRODUCTION,
    LeadStage.IN_PRODUCTION: LeadStage.DELIVERED,
    LeadStage.DELIVERED: LeadStage.AFTER_SALES,
    LeadStage.AFTER_SALES: None,
}


def classify_request(
    goal: str, additional_info: str = "", business_type: str = ""
) -> tuple[str, str]:
    text = " ".join((goal, additional_info, business_type)).casefold()
    excluded = (
        "e-commerce",
        "ecommerce",
        "loja virtual",
        "checkout",
        "pagamento online",
        "login",
        "dashboard",
        "aplicativo",
        "app mobile",
        "integração",
        "api",
        "automação de processo",
        "sistema sob medida",
    )
    if any(term in text for term in excluded):
        return (
            ServiceClassification.OUT_OF_SCOPE.value,
            "Solicitação menciona entrega não incluída na oferta de landing page.",
        )
    included = (
        "landing page",
        "landing",
        "página de captura",
        "pagina de captura",
        "página comercial",
        "pagina comercial",
        "página de vendas",
        "pagina de vendas",
    )
    if any(term in text for term in included):
        return (
            ServiceClassification.IN_SCOPE_LANDING_PAGE.value,
            "Solicitação menciona uma página comercial compatível; confirmar escopo no briefing.",
        )
    return (
        ServiceClassification.HUMAN_REVIEW.value,
        "A solicitação não permite confirmar automaticamente se cabe no escopo.",
    )


def _initial_classification(data: SalesInput) -> tuple[str, str]:
    return classify_request(data.goal, data.additional_info, data.business_type)


def get_lead(session: Session, organization_id: UUID, lead_id: UUID) -> SalesLead | None:
    return session.scalar(
        select(SalesLead).where(
            SalesLead.id == lead_id,
            SalesLead.organization_id == organization_id,
        )
    )


def list_leads(session: Session, organization_id: UUID, stage: LeadStage | None) -> list[SalesLead]:
    query = select(SalesLead).where(SalesLead.organization_id == organization_id)
    if stage is not None:
        query = query.where(SalesLead.stage == stage.value)
    return list(session.scalars(query.order_by(SalesLead.created_at.desc()).limit(200)).all())


def create_public_lead(
    session: Session,
    *,
    organization_id: UUID,
    data: PublicQuoteRequest,
    idempotency_key: str,
    privacy_notice_version: str,
) -> SalesLead:
    previous = session.scalar(
        select(SalesLead).where(
            SalesLead.organization_id == organization_id,
            SalesLead.idempotency_key == idempotency_key,
        )
    )
    if previous is not None:
        return previous
    classification, reason = _initial_classification(data)
    row = SalesLead(
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        source="PUBLIC_FORM",
        stage=LeadStage.NEW_LEAD.value,
        service_classification=classification,
        classification_reason=reason,
        name=data.name,
        company=data.company,
        email=data.email,
        whatsapp=data.whatsapp,
        business_type=data.business_type,
        goal=data.goal,
        desired_timeline=data.desired_timeline,
        additional_info=data.additional_info,
        privacy_notice_version=privacy_notice_version,
        consented_at=datetime.now(UTC),
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        # A concurrent retry may have committed this exact idempotency key.
        previous = session.scalar(
            select(SalesLead).where(
                SalesLead.organization_id == organization_id,
                SalesLead.idempotency_key == idempotency_key,
            )
        )
        if previous is not None:
            return previous
        raise
    add_audit_log(
        session,
        organization_id=organization_id,
        actor_user_id=None,
        action="sales_lead.public_created",
        resource_type="sales_lead",
        resource_id=row.id,
        details={"source": "PUBLIC_FORM", "stage": row.stage},
    )
    session.commit()
    session.refresh(row)
    return row


def create_manual_lead(
    session: Session,
    context: AuthContext,
    data: ManualLeadCreate,
) -> SalesLead:
    classification, reason = _initial_classification(data)
    row = SalesLead(
        organization_id=context.organization.id,
        created_by_user_id=context.user.id,
        source="MANUAL",
        stage=LeadStage.NEW_LEAD.value,
        service_classification=classification,
        classification_reason=reason,
        **data.model_dump(),
    )
    session.add(row)
    session.flush()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        actor_user_id=context.user.id,
        action="sales_lead.created",
        resource_type="sales_lead",
        resource_id=row.id,
        details={"source": "MANUAL", "stage": row.stage},
    )
    session.commit()
    session.refresh(row)
    return row


def update_stage(
    session: Session,
    context: AuthContext,
    lead: SalesLead,
    next_stage: LeadStage,
) -> SalesLead:
    current_stage = LeadStage(lead.stage)
    if current_stage != next_stage and _NEXT_STAGE[current_stage] != next_stage:
        raise ValueError("Etapa inválida; avance somente para a próxima fase do pipeline")
    if current_stage == next_stage:
        return lead
    lead.stage = next_stage.value
    add_audit_log(
        session,
        organization_id=context.organization.id,
        actor_user_id=context.user.id,
        action="sales_lead.stage_changed",
        resource_type="sales_lead",
        resource_id=lead.id,
        details={"from": current_stage.value, "to": next_stage.value},
    )
    session.commit()
    session.refresh(lead)
    return lead


def build_briefing(lead: SalesLead) -> LeadBriefingRead:
    missing = [
        label
        for value, label in (
            (lead.company, "Nome comercial da empresa"),
            (lead.business_type, "Segmento de atuação"),
            (lead.desired_timeline, "Prazo desejado confirmado"),
        )
        if not value
    ]
    missing.extend(["Textos e fatos aprovados pelo cliente", "Marca e imagens com direitos de uso"])
    return LeadBriefingRead(
        lead_id=lead.id,
        service_classification=ServiceClassification(lead.service_classification),
        classification_reason=lead.classification_reason,
        client_inputs={
            "name": lead.name,
            "company": lead.company,
            "business_type": lead.business_type,
            "goal": lead.goal,
            "desired_timeline": lead.desired_timeline,
            "additional_info": lead.additional_info,
        },
        missing_before_proposal=missing,
    )


def generate_proposal_draft(
    session: Session,
    context: AuthContext,
    lead: SalesLead,
) -> ProposalDraftRead:
    if lead.service_classification != ServiceClassification.IN_SCOPE_LANDING_PAGE.value:
        raise ValueError("Valide o escopo humano antes de preparar proposta para este pedido")
    if lead.stage not in {LeadStage.BRIEFING.value, LeadStage.PROPOSAL_PREPARATION.value}:
        raise ValueError("Conclua o contato e o briefing antes de preparar a proposta")
    body = f"""PROPOSTA COMERCIAL — RASCUNHO NÃO ENVIADO

Cliente: {lead.company or lead.name}
Serviço: Landing page comercial DevMarkia

ESCOPO
- Uma página comercial responsiva, até cinco seções e um CTA.
- Conteúdo baseado em fatos e materiais aprovados pelo cliente.
- Até duas rodadas de revisão de conteúdo/layout.
- Testes em viewport móvel e desktop; entrega dos arquivos e instruções.

PRAZO
Estimativa de cinco dias úteis após briefing, materiais e acessos completos.

PREÇO DE REFERÊNCIA
R$ 1.690, ainda sujeito à validação de custos, margem, tributos aplicáveis e
aprovação comercial final. Não constitui preço vinculante.

EXCLUSÕES
Domínio, hospedagem, mídia paga, integrações, CRM, pagamentos, copywriting
extenso, manutenção contínua e garantias de vendas, leads ou ranking.

PENDÊNCIAS ANTES DE ENVIO
Validar materiais, disponibilidade, condições de pagamento, validade,
cancelamento, direitos de uso e revisão jurídica/comercial. Nada foi enviado,
contratado ou aprovado pelo cliente.
"""
    lead.proposal_draft = body
    if lead.stage == LeadStage.BRIEFING.value:
        lead.stage = LeadStage.PROPOSAL_PREPARATION.value
    add_audit_log(
        session,
        organization_id=context.organization.id,
        actor_user_id=context.user.id,
        action="sales_lead.proposal_drafted",
        resource_type="sales_lead",
        resource_id=lead.id,
        details={"status": "DRAFT_NOT_SENT", "template": "devmarkia-landing-v1"},
    )
    session.commit()
    session.refresh(lead)
    return ProposalDraftRead(lead_id=lead.id, body=body)


def create_task(
    session: Session,
    context: AuthContext,
    lead: SalesLead,
    data: LeadTaskCreate,
) -> SalesLeadTask:
    task = SalesLeadTask(
        organization_id=context.organization.id,
        lead_id=lead.id,
        created_by_user_id=context.user.id,
        title=data.title,
        due_at=data.due_at,
        notes=data.notes,
    )
    session.add(task)
    session.flush()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        actor_user_id=context.user.id,
        action="sales_lead.task_created",
        resource_type="sales_lead_task",
        resource_id=task.id,
        details={"lead_id": str(lead.id)},
    )
    session.commit()
    session.refresh(task)
    return task


def list_tasks(session: Session, organization_id: UUID, lead_id: UUID) -> list[SalesLeadTask]:
    return list(
        session.scalars(
            select(SalesLeadTask)
            .where(
                SalesLeadTask.organization_id == organization_id,
                SalesLeadTask.lead_id == lead_id,
            )
            .order_by(SalesLeadTask.due_at, SalesLeadTask.created_at)
        ).all()
    )
