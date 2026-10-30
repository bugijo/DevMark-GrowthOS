from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext
from growthos.models import (
    AIGeneration,
    AIGenerationAlternative,
    AIGenerationAttempt,
    AIGenerationFeedback,
    AIUsageDaily,
    Membership,
    SalesLead,
    User,
)
from growthos.models.privacy import ConsentRecord, DataPurpose, PrivacyRequest, RetentionPolicy
from growthos.schemas_privacy import (
    ConsentCreate,
    ConsentRead,
    DataPurposeRead,
    PrivacyExportRead,
    PrivacyRequestCreate,
    PrivacyRequestRead,
    PrivacyResolution,
    RetentionPolicyRead,
    RetentionPolicyUpdate,
    RetentionRunCreate,
    RetentionRunRead,
)
from growthos.services.audit import add_audit_log

_DEFAULT_PURPOSES = (
    (
        "PLATFORM_OPERATION",
        "Operação da plataforma",
        "Autenticar, autorizar e executar os fluxos contratados.",
        "Execução de contrato",
        "Identidade, acesso e dados operacionais",
        1825,
    ),
    (
        "COMMUNICATION",
        "Comunicações operacionais",
        "Enviar avisos de aprovação, segurança e operação.",
        "Execução de contrato",
        "E-mail e preferências",
        730,
    ),
    (
        "AUDIT_SECURITY",
        "Auditoria e segurança",
        "Prevenir abuso, investigar incidentes e comprovar decisões.",
        "Legítimo interesse e obrigação legal",
        "Identificadores, eventos e metadados mínimos",
        2190,
    ),
)


def ensure_purposes(session: Session, context: AuthContext) -> list[DataPurpose]:
    rows = list(
        session.scalars(
            select(DataPurpose).where(DataPurpose.organization_id == context.organization.id)
        ).all()
    )
    existing = {row.code for row in rows}
    for code, name, purpose, basis, categories, days in _DEFAULT_PURPOSES:
        if code not in existing:
            row = DataPurpose(
                organization_id=context.organization.id,
                code=code,
                name=name,
                purpose=purpose,
                legal_basis=basis,
                data_categories=categories,
                retention_days=days,
                is_active=True,
            )
            session.add(row)
            rows.append(row)
    session.commit()
    return rows


def record_consent(session: Session, context: AuthContext, data: ConsentCreate) -> ConsentRead:
    valid_codes = {row.code for row in ensure_purposes(session, context)}
    if data.purpose_code not in valid_codes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Finalidade não reconhecida")
    row = ConsentRecord(
        organization_id=context.organization.id,
        user_id=context.user.id,
        purpose_code=data.purpose_code,
        policy_version=data.policy_version,
        accepted=data.accepted,
        source="WEB",
        created_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        actor_user_id=context.user.id,
        action="privacy.consent_recorded",
        resource_type="consent_record",
        resource_id=row.id,
        details={
            "purpose_code": data.purpose_code,
            "policy_version": data.policy_version,
            "accepted": data.accepted,
        },
    )
    session.commit()
    session.refresh(row)
    return ConsentRead.model_validate(row, from_attributes=True)


def list_consents(session: Session, context: AuthContext) -> list[ConsentRead]:
    rows = session.scalars(
        select(ConsentRecord)
        .where(
            ConsentRecord.organization_id == context.organization.id,
            ConsentRecord.user_id == context.user.id,
        )
        .order_by(ConsentRecord.created_at.desc())
    ).all()
    return [ConsentRead.model_validate(row, from_attributes=True) for row in rows]


def list_purposes(session: Session, context: AuthContext) -> list[DataPurposeRead]:
    return [
        DataPurposeRead.model_validate(row, from_attributes=True)
        for row in ensure_purposes(session, context)
    ]


def list_retention(session: Session, context: AuthContext) -> list[RetentionPolicyRead]:
    rows = session.scalars(
        select(RetentionPolicy)
        .where(RetentionPolicy.organization_id == context.organization.id)
        .order_by(RetentionPolicy.resource_type)
    ).all()
    return [RetentionPolicyRead.model_validate(row, from_attributes=True) for row in rows]


def save_retention(
    session: Session, context: AuthContext, resource_type: str, data: RetentionPolicyUpdate
) -> RetentionPolicyRead:
    row = session.scalar(
        select(RetentionPolicy).where(
            RetentionPolicy.organization_id == context.organization.id,
            RetentionPolicy.resource_type == resource_type,
        )
    )
    if row is None:
        row = RetentionPolicy(
            organization_id=context.organization.id,
            resource_type=resource_type,
            updated_by_user_id=context.user.id,
        )
        session.add(row)
    row.retention_days = data.retention_days
    row.legal_hold = data.legal_hold
    row.justification = data.justification
    row.updated_by_user_id = context.user.id
    session.flush()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        actor_user_id=context.user.id,
        action="privacy.retention_updated",
        resource_type="retention_policy",
        resource_id=row.id,
        details={
            "resource_type": resource_type,
            "retention_days": data.retention_days,
            "legal_hold": data.legal_hold,
        },
    )
    session.commit()
    session.refresh(row)
    return RetentionPolicyRead.model_validate(row, from_attributes=True)


def create_request(
    session: Session, context: AuthContext, data: PrivacyRequestCreate
) -> PrivacyRequestRead:
    row = PrivacyRequest(
        organization_id=context.organization.id,
        requested_by_user_id=context.user.id,
        subject_user_id=context.user.id,
        request_type=data.request_type,
        status="PENDING",
        reason=data.reason,
    )
    session.add(row)
    session.flush()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        actor_user_id=context.user.id,
        action="privacy.request_created",
        resource_type="privacy_request",
        resource_id=row.id,
        details={"request_type": data.request_type},
    )
    session.commit()
    session.refresh(row)
    return PrivacyRequestRead.model_validate(row, from_attributes=True)


def list_requests(
    session: Session, context: AuthContext, *, administrative: bool
) -> list[PrivacyRequestRead]:
    query = select(PrivacyRequest).where(PrivacyRequest.organization_id == context.organization.id)
    if not administrative:
        query = query.where(PrivacyRequest.subject_user_id == context.user.id)
    rows = session.scalars(query.order_by(PrivacyRequest.created_at.desc())).all()
    return [PrivacyRequestRead.model_validate(row, from_attributes=True) for row in rows]


def export_subject(session: Session, context: AuthContext) -> PrivacyExportRead:
    memberships = session.scalars(
        select(Membership).where(
            Membership.organization_id == context.organization.id,
            Membership.user_id == context.user.id,
        )
    ).all()
    generations = session.scalars(
        select(AIGeneration)
        .where(
            AIGeneration.organization_id == context.organization.id,
            AIGeneration.requested_by_user_id == context.user.id,
        )
        .order_by(AIGeneration.created_at)
    ).all()
    ai_export: list[dict[str, object]] = []
    for generation in generations:
        alternatives = session.scalars(
            select(AIGenerationAlternative)
            .where(
                AIGenerationAlternative.organization_id == context.organization.id,
                AIGenerationAlternative.generation_id == generation.id,
            )
            .order_by(AIGenerationAlternative.position)
        ).all()
        attempts = session.scalars(
            select(AIGenerationAttempt)
            .where(
                AIGenerationAttempt.organization_id == context.organization.id,
                AIGenerationAttempt.generation_id == generation.id,
            )
            .order_by(AIGenerationAttempt.created_at)
        ).all()
        feedback = session.scalars(
            select(AIGenerationFeedback)
            .where(
                AIGenerationFeedback.organization_id == context.organization.id,
                AIGenerationFeedback.generation_id == generation.id,
                AIGenerationFeedback.user_id == context.user.id,
            )
            .order_by(AIGenerationFeedback.created_at)
        ).all()
        ai_export.append(
            {
                "id": str(generation.id),
                "business_id": str(generation.business_id),
                "parent_generation_id": (
                    str(generation.parent_generation_id)
                    if generation.parent_generation_id
                    else None
                ),
                "task": generation.task,
                "instruction": generation.instruction,
                "context_snapshot": generation.context_snapshot,
                "provider": generation.provider,
                "model": generation.model,
                "used_fallback": generation.used_fallback,
                "status": generation.status,
                "cancelled_at": (
                    generation.cancelled_at.isoformat() if generation.cancelled_at else None
                ),
                "input_tokens": generation.input_tokens,
                "output_tokens": generation.output_tokens,
                "estimated_cost_usd": (
                    str(generation.estimated_cost_usd)
                    if generation.estimated_cost_usd is not None
                    else None
                ),
                "cost_usd": str(generation.cost_usd) if generation.cost_usd is not None else None,
                "cost_currency": generation.cost_currency,
                "cost_status": generation.cost_status,
                "cost_origin": generation.cost_origin,
                "created_at": generation.created_at.isoformat(),
                "alternatives": [
                    {
                        "id": str(item.id),
                        "position": item.position,
                        "payload": item.payload,
                        "is_sensitive": item.is_sensitive,
                        "applied_content_item_id": (
                            str(item.applied_content_item_id)
                            if item.applied_content_item_id
                            else None
                        ),
                        "applied_content_version_id": (
                            str(item.applied_content_version_id)
                            if item.applied_content_version_id
                            else None
                        ),
                        "applied_at": item.applied_at.isoformat() if item.applied_at else None,
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in alternatives
                ],
                "attempts": [
                    {
                        "provider": item.provider,
                        "model": item.model,
                        "status": item.status,
                        "duration_ms": item.duration_ms,
                        "cost_usd": str(item.cost_usd) if item.cost_usd is not None else None,
                        "cost_currency": item.cost_currency,
                        "cost_status": item.cost_status,
                        "cost_origin": item.cost_origin,
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in attempts
                ],
                "feedback": [
                    {
                        "rating": item.rating,
                        "comment": item.comment,
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in feedback
                ],
            }
        )
    return PrivacyExportRead(
        generated_at=datetime.now(UTC),
        organization={"id": str(context.organization.id), "name": context.organization.name},
        subject={
            "id": str(context.user.id),
            "name": context.user.name,
            "email": context.user.email,
        },
        memberships=[
            {
                "id": str(row.id),
                "role": row.role.value,
                "business_id": str(row.business_id) if row.business_id else None,
            }
            for row in memberships
        ],
        consents=list_consents(session, context),
        requests=list_requests(session, context, administrative=False),
        ai_generations=ai_export,
    )


def _anonymize_ai_subject(
    session: Session, *, organization_id: UUID, subject_user_id: UUID
) -> dict[str, int]:
    generation_ids = list(
        session.scalars(
            select(AIGeneration.id).where(
                AIGeneration.organization_id == organization_id,
                AIGeneration.requested_by_user_id == subject_user_id,
            )
        ).all()
    )
    if generation_ids:
        session.execute(
            update(AIGeneration)
            .where(
                AIGeneration.organization_id == organization_id,
                AIGeneration.id.in_(generation_ids),
            )
            .values(
                requested_by_user_id=None,
                cancelled_by_user_id=None,
                instruction="[ANONIMIZADO POR SOLICITAÇÃO LGPD]",
                context_snapshot={"privacy_status": "ANONYMIZED"},
            )
        )
        session.execute(
            update(AIGenerationAlternative)
            .where(
                AIGenerationAlternative.organization_id == organization_id,
                AIGenerationAlternative.generation_id.in_(generation_ids),
            )
            .values(payload={"privacy_status": "ANONYMIZED"})
        )
    session.execute(
        update(AIGeneration)
        .where(
            AIGeneration.organization_id == organization_id,
            AIGeneration.cancelled_by_user_id == subject_user_id,
        )
        .values(cancelled_by_user_id=None)
    )
    session.execute(
        update(AIGenerationAlternative)
        .where(
            AIGenerationAlternative.organization_id == organization_id,
            AIGenerationAlternative.applied_by_user_id == subject_user_id,
        )
        .values(applied_by_user_id=None)
    )
    feedback_ids = list(
        session.scalars(
            select(AIGenerationFeedback.id).where(
                AIGenerationFeedback.organization_id == organization_id,
                AIGenerationFeedback.user_id == subject_user_id,
            )
        ).all()
    )
    if feedback_ids:
        session.execute(
            update(AIGenerationFeedback)
            .where(
                AIGenerationFeedback.organization_id == organization_id,
                AIGenerationFeedback.id.in_(feedback_ids),
            )
            .values(user_id=None, comment="[ANONIMIZADO POR SOLICITAÇÃO LGPD]")
        )
    return {"generations": len(generation_ids), "feedback": len(feedback_ids)}


def run_retention(
    session: Session, context: AuthContext, data: RetentionRunCreate
) -> RetentionRunRead:
    policy = session.scalar(
        select(RetentionPolicy).where(
            RetentionPolicy.organization_id == context.organization.id,
            RetentionPolicy.resource_type == data.resource_type,
        )
    )
    if policy is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Política de retenção não configurada")
    if policy.legal_hold:
        raise HTTPException(status.HTTP_409_CONFLICT, "Recurso está sob retenção legal")
    cutoff = datetime.now(UTC) - timedelta(days=policy.retention_days)
    organization_id = context.organization.id
    affected = 0
    if data.resource_type == "ai_generation_feedback":
        feedback_predicate = (
            AIGenerationFeedback.organization_id == organization_id,
            AIGenerationFeedback.created_at < cutoff,
        )
        affected = (
            session.scalar(
                select(func.count()).select_from(AIGenerationFeedback).where(*feedback_predicate)
            )
            or 0
        )
        if not data.dry_run:
            session.execute(delete(AIGenerationFeedback).where(*feedback_predicate))
    elif data.resource_type == "ai_generation_attempts":
        attempts_predicate = (
            AIGenerationAttempt.organization_id == organization_id,
            AIGenerationAttempt.created_at < cutoff,
        )
        affected = (
            session.scalar(
                select(func.count()).select_from(AIGenerationAttempt).where(*attempts_predicate)
            )
            or 0
        )
        if not data.dry_run:
            session.execute(delete(AIGenerationAttempt).where(*attempts_predicate))
    elif data.resource_type == "ai_generation_alternatives":
        alternatives_predicate = (
            AIGenerationAlternative.organization_id == organization_id,
            AIGenerationAlternative.created_at < cutoff,
        )
        affected = (
            session.scalar(
                select(func.count())
                .select_from(AIGenerationAlternative)
                .where(*alternatives_predicate)
            )
            or 0
        )
        if not data.dry_run:
            session.execute(delete(AIGenerationAlternative).where(*alternatives_predicate))
    elif data.resource_type == "ai_usage_daily":
        cutoff_date = cutoff.date()
        usage_predicate = (
            AIUsageDaily.organization_id == organization_id,
            AIUsageDaily.usage_date < cutoff_date,
        )
        affected = (
            session.scalar(select(func.count()).select_from(AIUsageDaily).where(*usage_predicate))
            or 0
        )
        if not data.dry_run:
            session.execute(delete(AIUsageDaily).where(*usage_predicate))
    elif data.resource_type == "ai_generation_snapshots":
        snapshots_predicate = (
            AIGeneration.organization_id == organization_id,
            AIGeneration.created_at < cutoff,
            AIGeneration.context_snapshot != {"retention_status": "EXPIRED"},
        )
        affected = (
            session.scalar(
                select(func.count()).select_from(AIGeneration).where(*snapshots_predicate)
            )
            or 0
        )
        if not data.dry_run:
            session.execute(
                update(AIGeneration)
                .where(*snapshots_predicate)
                .values(context_snapshot={"retention_status": "EXPIRED"}, instruction="")
            )
    elif data.resource_type == "ai_generation_errors":
        errors_predicate = (
            AIGenerationAttempt.organization_id == organization_id,
            AIGenerationAttempt.created_at < cutoff,
            AIGenerationAttempt.error_code.is_not(None),
        )
        affected = (
            session.scalar(
                select(func.count()).select_from(AIGenerationAttempt).where(*errors_predicate)
            )
            or 0
        )
        if not data.dry_run:
            session.execute(
                update(AIGenerationAttempt).where(*errors_predicate).values(error_code=None)
            )
    elif data.resource_type == "sales_leads":
        leads_predicate = (
            SalesLead.organization_id == organization_id,
            SalesLead.created_at < cutoff,
        )
        affected = (
            session.scalar(select(func.count()).select_from(SalesLead).where(*leads_predicate)) or 0
        )
        if not data.dry_run:
            session.execute(delete(SalesLead).where(*leads_predicate))
    else:
        # Sem vínculo de “alternativa aplicada” nesta versão, gerações são preservadas e
        # seus dados pessoais são minimizados pela política específica de snapshots.
        generations_predicate = (
            AIGeneration.organization_id == organization_id,
            AIGeneration.created_at < cutoff,
        )
        affected = (
            session.scalar(
                select(func.count()).select_from(AIGeneration).where(*generations_predicate)
            )
            or 0
        )
    audit = add_audit_log(
        session,
        organization_id=organization_id,
        actor_user_id=context.user.id,
        action="privacy.retention_dry_run" if data.dry_run else "privacy.retention_executed",
        resource_type="retention_policy",
        resource_id=policy.id,
        details={
            "target_resource": data.resource_type,
            "cutoff_at": cutoff.isoformat(),
            "affected_count": affected,
            "dry_run": data.dry_run,
        },
    )
    session.commit()
    return RetentionRunRead(
        resource_type=data.resource_type,
        dry_run=data.dry_run,
        cutoff_at=cutoff,
        affected_count=affected,
        audit_log_id=audit.id,
    )


def resolve_request(
    session: Session, context: AuthContext, request_id: UUID, data: PrivacyResolution
) -> PrivacyRequestRead:
    row = session.scalar(
        select(PrivacyRequest).where(
            PrivacyRequest.id == request_id,
            PrivacyRequest.organization_id == context.organization.id,
        )
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitação não encontrada")
    if row.status != "PENDING":
        raise HTTPException(status.HTTP_409_CONFLICT, "Solicitação já processada")
    now = datetime.now(UTC)
    row.status = "COMPLETED" if data.decision == "COMPLETE" else "REJECTED"
    row.resolution_notes = data.notes
    row.processed_by_user_id = context.user.id
    row.processed_at = now
    if row.request_type == "DELETION" and data.decision == "COMPLETE":
        ai_anonymized = _anonymize_ai_subject(
            session,
            organization_id=context.organization.id,
            subject_user_id=row.subject_user_id,
        )
        memberships = session.scalars(
            select(Membership).where(
                Membership.organization_id == context.organization.id,
                Membership.user_id == row.subject_user_id,
            )
        ).all()
        for membership in memberships:
            membership.is_active = False
        other_active = session.scalar(
            select(Membership.id)
            .where(
                Membership.user_id == row.subject_user_id,
                Membership.organization_id != context.organization.id,
                Membership.is_active.is_(True),
            )
            .limit(1)
        )
        if other_active is None:
            subject = session.get(User, row.subject_user_id)
            if subject:
                subject.email = f"anon-{str(subject.id).replace('-', '')}@redacted.invalid"
                subject.name = "Usuário anonimizado"
                subject.is_active = False
                subject.session_version += 1
    add_audit_log(
        session,
        organization_id=context.organization.id,
        actor_user_id=context.user.id,
        action="privacy.request_resolved",
        resource_type="privacy_request",
        resource_id=row.id,
        details={
            "request_type": row.request_type,
            "decision": data.decision,
            "audit_logs_preserved": True,
            "ai_anonymized": ai_anonymized if row.request_type == "DELETION" else {},
        },
    )
    session.commit()
    session.refresh(row)
    return PrivacyRequestRead.model_validate(row, from_attributes=True)
