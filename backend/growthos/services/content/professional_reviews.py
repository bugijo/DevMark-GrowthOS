from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext
from growthos.domain.enums import (
    ApprovalStage,
    ApprovalStatus,
    ContentStatus,
    ProfessionalReviewDecision,
)
from growthos.domain.permissions import Capability, has_capability
from growthos.models import Approval, ContentItem, ContentVersion, ProfessionalContentReview
from growthos.models.base import utcnow
from growthos.schemas import ContentRead, ProfessionalReviewCreate, ProfessionalReviewRead
from growthos.services.audit import add_audit_log
from growthos.services.content.common import transition
from growthos.services.content.read_models import (
    get_content,
    get_current_version,
    serialize_content,
)


def _require_explicit_grant(context: AuthContext) -> None:
    if not (
        has_capability(
            context.membership.role,
            Capability.CONTENT_REVIEW_PROFESSIONAL,
        )
        and context.membership.professional_review_granted
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "A revisão profissional exige uma concessão explícita ativa",
        )


def ensure_professional_approval(
    session: Session,
    content: ContentItem,
    version: ContentVersion,
) -> None:
    """Bloqueia a aprovação comum/publicação quando o snapshot atual é sensível."""

    if version.sensitivity_provider == "legacy_unassessed":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta versão legada precisa de uma nova revisão classificada antes de avançar",
        )
    if not version.is_sensitive:
        return
    decision = session.scalar(
        select(ProfessionalContentReview.decision).where(
            ProfessionalContentReview.organization_id == content.organization_id,
            ProfessionalContentReview.business_id == content.business_id,
            ProfessionalContentReview.content_item_id == content.id,
            ProfessionalContentReview.content_version_id == version.id,
        )
    )
    if decision != ProfessionalReviewDecision.APPROVED:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta versão sensível precisa de aprovação profissional antes da aprovação comum",
        )


def list_professional_reviews(
    session: Session,
    context: AuthContext,
    content_id: UUID,
) -> list[ProfessionalReviewRead]:
    content = get_content(session, context, content_id)
    reviews = session.scalars(
        select(ProfessionalContentReview)
        .where(
            ProfessionalContentReview.organization_id == content.organization_id,
            ProfessionalContentReview.business_id == content.business_id,
            ProfessionalContentReview.content_item_id == content.id,
        )
        .order_by(ProfessionalContentReview.created_at, ProfessionalContentReview.id)
    ).all()
    return [ProfessionalReviewRead.model_validate(review) for review in reviews]


def review_current_version(
    session: Session,
    context: AuthContext,
    content_id: UUID,
    payload: ProfessionalReviewCreate,
) -> ContentRead:
    # Resolve o recurso no tenant antes de avaliar a concessão, evitando enumeração cruzada.
    content = get_content(session, context, content_id, for_update=True)
    _require_explicit_grant(context)
    version = get_current_version(session, content)
    if not version.is_sensitive:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A versão atual não requer revisão profissional",
        )
    if content.status not in {ContentStatus.INTERNAL_REVIEW, ContentStatus.CLIENT_REVIEW}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A revisão profissional só pode ocorrer durante uma etapa de revisão",
        )
    existing = session.scalar(
        select(ProfessionalContentReview.id).where(
            ProfessionalContentReview.organization_id == content.organization_id,
            ProfessionalContentReview.business_id == content.business_id,
            ProfessionalContentReview.content_item_id == content.id,
            ProfessionalContentReview.content_version_id == version.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta versão já possui uma decisão profissional",
        )

    review = ProfessionalContentReview(
        organization_id=content.organization_id,
        business_id=content.business_id,
        content_item_id=content.id,
        content_version_id=version.id,
        reviewer_user_id=context.user.id,
        reviewer_membership_id=context.membership.id,
        decision=payload.decision,
        justification=payload.justification.strip(),
    )
    session.add(review)
    previous = content.status
    cancelled_components: list[str] = []
    if payload.decision == ProfessionalReviewDecision.CHANGES_REQUESTED:
        previous = transition(content, ContentStatus.CHANGES_REQUESTED)
        decided_at = utcnow()
        pending = session.scalars(
            select(Approval)
            .where(
                Approval.organization_id == content.organization_id,
                Approval.business_id == content.business_id,
                Approval.content_item_id == content.id,
                Approval.content_version_id == version.id,
                Approval.stage == ApprovalStage.CLIENT,
                Approval.status == ApprovalStatus.PENDING,
            )
            .with_for_update()
        ).all()
        for approval in pending:
            approval.status = ApprovalStatus.CANCELLED
            approval.decided_by_user_id = context.user.id
            approval.decided_at = decided_at
            cancelled_components.append(approval.component.value)

    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta versão já possui uma decisão profissional",
        ) from exc
    add_audit_log(
        session,
        organization_id=content.organization_id,
        business_id=content.business_id,
        actor_user_id=context.user.id,
        action=(
            "content.professional_review_approved"
            if payload.decision == ProfessionalReviewDecision.APPROVED
            else "content.professional_changes_requested"
        ),
        resource_type="content_item",
        resource_id=content.id,
        details={
            "content_version_id": str(version.id),
            "professional_review_id": str(review.id),
            "reviewer_membership_id": str(context.membership.id),
            "decision": payload.decision.value,
            "justification_present": True,
            "sensitivity_codes": list(version.sensitivity_codes),
            "from": previous.value,
            "to": content.status.value,
            "cancelled_components": cancelled_components,
        },
    )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta versão já possui uma decisão profissional",
        ) from exc
    return serialize_content(session, content, context)
