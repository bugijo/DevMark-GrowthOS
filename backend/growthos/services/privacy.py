from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext
from growthos.models import Membership, User
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
        },
    )
    session.commit()
    session.refresh(row)
    return PrivacyRequestRead.model_validate(row, from_attributes=True)
