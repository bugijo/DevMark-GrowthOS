from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext
from growthos.domain.enums import (
    ApprovalComponent,
    ApprovalStage,
    ApprovalStatus,
    ContentStatus,
    Role,
)
from growthos.models import (
    Approval,
    ContentItem,
    ContentVersion,
    ContentVersionMedia,
    Membership,
    Notification,
    User,
)
from growthos.models.base import utcnow
from growthos.schemas import ContentRead, DecisionRequest
from growthos.services.audit import add_audit_log
from growthos.services.content.common import transition
from growthos.services.content.read_models import (
    get_content,
    get_current_version,
    serialize_content,
)
from growthos.services.email_jobs import enqueue_notification_email


def _pending_approval(
    session: Session,
    content: ContentItem,
    version: ContentVersion,
    component: ApprovalComponent,
) -> Approval:
    approval = session.scalar(
        select(Approval)
        .where(
            Approval.organization_id == content.organization_id,
            Approval.business_id == content.business_id,
            Approval.content_item_id == content.id,
            Approval.content_version_id == version.id,
            Approval.stage == ApprovalStage.CLIENT,
            Approval.component == component,
            Approval.status == ApprovalStatus.PENDING,
        )
        .with_for_update()
    )
    if approval is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Não há aprovação pendente para esta versão")
    return approval


def _all_components_approved(
    session: Session,
    content: ContentItem,
    version: ContentVersion,
) -> bool:
    rows = session.execute(
        select(Approval.component, Approval.status).where(
            Approval.organization_id == content.organization_id,
            Approval.business_id == content.business_id,
            Approval.content_item_id == content.id,
            Approval.content_version_id == version.id,
            Approval.stage == ApprovalStage.CLIENT,
        )
    ).all()
    statuses = {component: approval_status for component, approval_status in rows}
    return all(
        statuses.get(component) == ApprovalStatus.APPROVED for component in ApprovalComponent
    )


def _notify_agency(
    session: Session,
    content: ContentItem,
    title: str,
    message: str,
    *,
    email_key: str,
) -> None:
    recipients = session.execute(
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.organization_id == content.organization_id,
            Membership.is_active.is_(True),
            User.is_active.is_(True),
            Membership.role.in_(
                [
                    Role.SUPER_ADMIN,
                    Role.AGENCY_ADMIN,
                    Role.STRATEGIST,
                    Role.CONTENT_EDITOR,
                    Role.DESIGNER,
                ]
            ),
            or_(
                Membership.business_id.is_(None),
                Membership.business_id == content.business_id,
            ),
        )
    ).all()
    for _user, membership in recipients:
        notification = Notification(
            organization_id=content.organization_id,
            business_id=content.business_id,
            recipient_user_id=membership.user_id,
            type="CONTENT_DECISION",
            title=title,
            message=message,
            resource_type="content_item",
            resource_id=content.id,
        )
        session.add(notification)
        enqueue_notification_email(
            session,
            notification,
            idempotency_key=f"{email_key}:{membership.id}",
        )


def submit_internal(
    session: Session,
    context: AuthContext,
    content_id: UUID,
) -> ContentRead:
    content = get_content(session, context, content_id, for_update=True)
    previous = transition(content, ContentStatus.INTERNAL_REVIEW)
    version = get_current_version(session, content)
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=content.business_id,
        actor_user_id=context.user.id,
        action="content.submitted_internal",
        resource_type="content_item",
        resource_id=content.id,
        details={"from": previous.value, "to": content.status.value, "version_id": str(version.id)},
    )
    session.commit()
    return serialize_content(session, content, context)


def send_to_client(
    session: Session,
    context: AuthContext,
    content_id: UUID,
) -> ContentRead:
    content = get_content(session, context, content_id, for_update=True)
    version = get_current_version(session, content)
    reviewers = session.execute(
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.organization_id == context.organization.id,
            Membership.business_id == content.business_id,
            Membership.is_active.is_(True),
            Membership.role.in_([Role.CLIENT_OWNER, Role.CLIENT_REVIEWER]),
            User.is_active.is_(True),
        )
    ).all()
    if not reviewers:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cadastre um revisor do cliente antes de enviar",
        )
    previous = transition(content, ContentStatus.CLIENT_REVIEW)
    for component in ApprovalComponent:
        session.add(
            Approval(
                organization_id=context.organization.id,
                business_id=content.business_id,
                content_item_id=content.id,
                content_version_id=version.id,
                stage=ApprovalStage.CLIENT,
                component=component,
                status=ApprovalStatus.PENDING,
                requested_by_user_id=context.user.id,
            )
        )
    for _user, reviewer in reviewers:
        notification = Notification(
            organization_id=context.organization.id,
            business_id=content.business_id,
            recipient_user_id=reviewer.user_id,
            type="CONTENT_REVIEW_REQUESTED",
            title="Novo conteúdo para revisar",
            message="A equipe enviou um conteúdo para sua aprovação.",
            resource_type="content_item",
            resource_id=content.id,
        )
        session.add(notification)
        enqueue_notification_email(
            session,
            notification,
            idempotency_key=f"content-review:{content.id}:{version.id}:{reviewer.id}",
        )
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=content.business_id,
        actor_user_id=context.user.id,
        action="content.sent_to_client",
        resource_type="content_item",
        resource_id=content.id,
        details={
            "from": previous.value,
            "to": content.status.value,
            "version_id": str(version.id),
            "reviewer_count": len(reviewers),
            "components": [component.value for component in ApprovalComponent],
        },
    )
    session.commit()
    return serialize_content(session, content, context)


def approve_content(
    session: Session,
    context: AuthContext,
    content_id: UUID,
    payload: DecisionRequest | None,
) -> ContentRead:
    content = get_content(session, context, content_id, for_update=True)
    if context.membership.business_id != content.business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Aprovação fora do cliente permitido")
    version = get_current_version(session, content)
    approvals = list(
        session.scalars(
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
    )
    if not approvals:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Não há aprovação pendente para esta versão",
        )
    decided_at = utcnow()
    for approval in approvals:
        approval.status = ApprovalStatus.APPROVED
        approval.decided_by_user_id = context.user.id
        approval.decision_comment = payload.comment if payload else None
        approval.decided_at = decided_at
    session.flush()
    if not _all_components_approved(session, content, version):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Texto e imagem precisam estar disponíveis para aprovação",
        )
    previous = transition(content, ContentStatus.APPROVED)
    _notify_agency(
        session,
        content,
        "Conteúdo aprovado",
        "O cliente aprovou o conteúdo enviado.",
        email_key=f"content-decision:{content.id}:{version.id}:approved",
    )
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=content.business_id,
        actor_user_id=context.user.id,
        action="content.approved_by_client",
        resource_type="content_item",
        resource_id=content.id,
        details={
            "from": previous.value,
            "to": content.status.value,
            "version_id": str(version.id),
            "components": sorted(approval.component.value for approval in approvals),
        },
    )
    session.commit()
    return serialize_content(session, content, context)


def approve_content_component(
    session: Session,
    context: AuthContext,
    content_id: UUID,
    component: ApprovalComponent,
    payload: DecisionRequest | None,
) -> ContentRead:
    content = get_content(session, context, content_id, for_update=True)
    if context.membership.business_id != content.business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Aprovação fora do cliente permitido")
    version = get_current_version(session, content)
    if component == ApprovalComponent.IMAGE:
        media_id = session.scalar(
            select(ContentVersionMedia.media_asset_id).where(
                ContentVersionMedia.organization_id == content.organization_id,
                ContentVersionMedia.business_id == content.business_id,
                ContentVersionMedia.content_version_id == version.id,
            )
        )
        if media_id is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Vincule uma imagem antes de aprovar o componente visual",
            )
    approval = _pending_approval(session, content, version, component)
    approval.status = ApprovalStatus.APPROVED
    approval.decided_by_user_id = context.user.id
    approval.decision_comment = payload.comment if payload else None
    approval.decided_at = utcnow()
    session.flush()
    previous = content.status
    completed = _all_components_approved(session, content, version)
    if completed:
        previous = transition(content, ContentStatus.APPROVED)
        title = "Conteúdo aprovado"
        message = "O cliente aprovou o texto e a imagem do conteúdo."
        action = "content.approved_by_client"
    else:
        title = f"{component.value.title()} aprovado"
        message = "O cliente aprovou uma parte do conteúdo; outra decisão ainda está pendente."
        action = "content.component_approved_by_client"
    _notify_agency(
        session,
        content,
        title,
        message,
        email_key=(
            f"content-decision:{content.id}:{version.id}:approved:{component.value.lower()}"
        ),
    )
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=content.business_id,
        actor_user_id=context.user.id,
        action=action,
        resource_type="content_item",
        resource_id=content.id,
        details={
            "component": component.value,
            "from": previous.value,
            "to": content.status.value,
            "version_id": str(version.id),
            "all_components_approved": completed,
        },
    )
    session.commit()
    return serialize_content(session, content, context)


def request_component_changes(
    session: Session,
    context: AuthContext,
    content_id: UUID,
    component: ApprovalComponent,
    comment: str,
) -> ContentRead:
    content = get_content(session, context, content_id, for_update=True)
    if context.membership.business_id != content.business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Revisão fora do cliente permitido")
    current = get_current_version(session, content)
    approval = _pending_approval(session, content, current, component)
    previous = transition(content, ContentStatus.CHANGES_REQUESTED)
    decided_at = utcnow()
    approval.status = ApprovalStatus.CHANGES_REQUESTED
    approval.decided_by_user_id = context.user.id
    approval.decision_comment = comment
    approval.decided_at = decided_at
    obsolete = list(
        session.scalars(
            select(Approval)
            .where(
                Approval.organization_id == content.organization_id,
                Approval.business_id == content.business_id,
                Approval.content_item_id == content.id,
                Approval.content_version_id == current.id,
                Approval.stage == ApprovalStage.CLIENT,
                Approval.component != component,
                Approval.status == ApprovalStatus.PENDING,
            )
            .with_for_update()
        ).all()
    )
    for pending in obsolete:
        pending.status = ApprovalStatus.CANCELLED
        pending.decided_by_user_id = context.user.id
        pending.decided_at = decided_at
    _notify_agency(
        session,
        content,
        "Alteração solicitada",
        f"O cliente pediu uma alteração em {component.value.lower()}.",
        email_key=(f"content-decision:{content.id}:{current.id}:changes:{component.value.lower()}"),
    )
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=content.business_id,
        actor_user_id=context.user.id,
        action="content.changes_requested",
        resource_type="content_item",
        resource_id=content.id,
        details={
            "component": component.value,
            "from": previous.value,
            "to": content.status.value,
            "reviewed_version_id": str(current.id),
            "comment_present": bool(comment),
            "cancelled_components": [pending.component.value for pending in obsolete],
        },
    )
    session.commit()
    return serialize_content(session, content, context)
