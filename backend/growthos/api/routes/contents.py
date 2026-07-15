from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.config import Settings, get_settings
from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    get_scoped_business,
    require_csrf,
    require_role,
)
from growthos.domain.content import InvalidContentTransition, validate_transition
from growthos.domain.enums import ApprovalStage, ApprovalStatus, ContentStatus, Role
from growthos.models import (
    Approval,
    BrandProfile,
    ContentItem,
    ContentVersion,
    Membership,
    Notification,
)
from growthos.schemas import (
    ChangesRequest,
    ContentGenerateRequest,
    ContentRead,
    ContentVersionRead,
    DecisionRequest,
)
from growthos.services.audit import add_audit_log
from growthos.services.providers import MockTextProvider, TextGenerationRequest

router = APIRouter()

_AGENCY_WRITERS = (Role.SUPER_ADMIN, Role.AGENCY_ADMIN)
_CLIENT_REVIEWERS = (Role.CLIENT_OWNER, Role.CLIENT_REVIEWER)


def _get_content(session: Session, context: AuthContext, content_id: UUID) -> ContentItem:
    query = select(ContentItem).where(
        ContentItem.id == content_id,
        ContentItem.organization_id == context.organization.id,
    )
    if context.membership.business_id is not None:
        query = query.where(ContentItem.business_id == context.membership.business_id)
    content = session.scalar(query)
    if content is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conteúdo não encontrado")
    return content


def _get_current_version(session: Session, content: ContentItem) -> ContentVersion:
    if content.current_version_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Conteúdo sem versão atual")
    version = session.scalar(
        select(ContentVersion).where(
            ContentVersion.id == content.current_version_id,
            ContentVersion.organization_id == content.organization_id,
            ContentVersion.business_id == content.business_id,
            ContentVersion.content_item_id == content.id,
        )
    )
    if version is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Versão atual inconsistente")
    return version


def _serialize(session: Session, content: ContentItem) -> ContentRead:
    version = _get_current_version(session, content)
    return ContentRead(
        id=content.id,
        organization_id=content.organization_id,
        business_id=content.business_id,
        status=content.status,
        current_version=ContentVersionRead.model_validate(version),
        created_at=content.created_at,
        updated_at=content.updated_at,
    )


def _transition(content: ContentItem, target: ContentStatus) -> ContentStatus:
    previous = content.status
    try:
        validate_transition(previous, target)
    except InvalidContentTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    content.status = target
    return previous


def _pending_approval(
    session: Session,
    content: ContentItem,
    version: ContentVersion,
) -> Approval:
    approval = session.scalar(
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
    )
    if approval is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Não há aprovação pendente para esta versão")
    return approval


def _notify_agency(session: Session, content: ContentItem, title: str, message: str) -> None:
    recipients = session.scalars(
        select(Membership).where(
            Membership.organization_id == content.organization_id,
            Membership.is_active.is_(True),
            Membership.role.in_([Role.AGENCY_ADMIN, Role.SUPER_ADMIN]),
        )
    ).all()
    for membership in recipients:
        session.add(
            Notification(
                organization_id=content.organization_id,
                business_id=content.business_id,
                recipient_user_id=membership.user_id,
                type="CONTENT_DECISION",
                title=title,
                message=message,
                resource_type="content_item",
                resource_id=content.id,
            )
        )


@router.post("/generate", response_model=ContentRead, status_code=status.HTTP_201_CREATED)
def generate_content(
    payload: ContentGenerateRequest,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ContentRead:
    require_role(context, *_AGENCY_WRITERS)
    if settings.ai_provider != "mock":
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Somente o provider mock está habilitado nesta versão",
        )
    business = get_scoped_business(session, context, payload.business_id)
    brand = session.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == context.organization.id,
            BrandProfile.business_id == business.id,
        )
    )
    provider = MockTextProvider()
    result = provider.generate(
        TextGenerationRequest(
            brand_name=brand.brand_name if brand else business.name,
            objective=payload.objective,
            channel=payload.channel,
            format=payload.format,
            audience=brand.audience if brand else "",
            tone_of_voice=brand.tone_of_voice if brand else "",
            cta=(brand.calls_to_action[0] if brand and brand.calls_to_action else ""),
        )
    )
    content = ContentItem(
        organization_id=context.organization.id,
        business_id=business.id,
        status=ContentStatus.DRAFT,
        created_by_user_id=context.user.id,
    )
    session.add(content)
    session.flush()
    version = ContentVersion(
        organization_id=context.organization.id,
        business_id=business.id,
        content_item_id=content.id,
        version_number=1,
        title=result.title,
        caption=result.caption,
        channel=payload.channel,
        format=payload.format,
        objective=payload.objective,
        audience=result.audience,
        cta=result.cta,
        provider_name=result.provider_name,
        created_by_user_id=context.user.id,
    )
    session.add(version)
    session.flush()
    content.current_version_id = version.id
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="content.generated",
        resource_type="content_item",
        resource_id=content.id,
        details={"provider": result.provider_name, "version": 1},
    )
    session.commit()
    return _serialize(session, content)


@router.get("", response_model=list[ContentRead])
def list_contents(
    business_id: UUID | None = Query(default=None),
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[ContentRead]:
    query = select(ContentItem).where(ContentItem.organization_id == context.organization.id)
    limited_business = context.membership.business_id
    if limited_business is not None:
        if business_id is not None and business_id != limited_business:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
        query = query.where(ContentItem.business_id == limited_business)
    elif business_id is not None:
        get_scoped_business(session, context, business_id)
        query = query.where(ContentItem.business_id == business_id)
    contents = session.scalars(query.order_by(ContentItem.created_at.desc())).all()
    return [_serialize(session, content) for content in contents]


@router.get("/{content_id}", response_model=ContentRead)
def get_content(
    content_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> ContentRead:
    return _serialize(session, _get_content(session, context, content_id))


@router.post("/{content_id}/submit-internal", response_model=ContentRead)
def submit_internal(
    content_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_role(context, *_AGENCY_WRITERS)
    content = _get_content(session, context, content_id)
    previous = _transition(content, ContentStatus.INTERNAL_REVIEW)
    version = _get_current_version(session, content)
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
    return _serialize(session, content)


@router.post("/{content_id}/send-to-client", response_model=ContentRead)
def send_to_client(
    content_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_role(context, *_AGENCY_WRITERS)
    content = _get_content(session, context, content_id)
    version = _get_current_version(session, content)
    reviewers = session.scalars(
        select(Membership).where(
            Membership.organization_id == context.organization.id,
            Membership.business_id == content.business_id,
            Membership.is_active.is_(True),
            Membership.role.in_([Role.CLIENT_OWNER, Role.CLIENT_REVIEWER]),
        )
    ).all()
    if not reviewers:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cadastre um revisor do cliente antes de enviar",
        )
    previous = _transition(content, ContentStatus.CLIENT_REVIEW)
    approval = Approval(
        organization_id=context.organization.id,
        business_id=content.business_id,
        content_item_id=content.id,
        content_version_id=version.id,
        stage=ApprovalStage.CLIENT,
        status=ApprovalStatus.PENDING,
        requested_by_user_id=context.user.id,
    )
    session.add(approval)
    for reviewer in reviewers:
        session.add(
            Notification(
                organization_id=context.organization.id,
                business_id=content.business_id,
                recipient_user_id=reviewer.user_id,
                type="CONTENT_REVIEW_REQUESTED",
                title="Novo conteúdo para revisar",
                message="A equipe enviou um conteúdo para sua aprovação.",
                resource_type="content_item",
                resource_id=content.id,
            )
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
        },
    )
    session.commit()
    return _serialize(session, content)


@router.post("/{content_id}/approve", response_model=ContentRead)
def approve_content(
    content_id: UUID,
    payload: DecisionRequest | None = None,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_role(context, *_CLIENT_REVIEWERS)
    content = _get_content(session, context, content_id)
    if context.membership.business_id != content.business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Aprovação fora do cliente permitido")
    version = _get_current_version(session, content)
    approval = _pending_approval(session, content, version)
    previous = _transition(content, ContentStatus.APPROVED)
    approval.status = ApprovalStatus.APPROVED
    approval.decided_by_user_id = context.user.id
    approval.decision_comment = payload.comment if payload else None
    from growthos.models.base import utcnow

    approval.decided_at = utcnow()
    _notify_agency(
        session,
        content,
        "Conteúdo aprovado",
        "O cliente aprovou o conteúdo enviado.",
    )
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=content.business_id,
        actor_user_id=context.user.id,
        action="content.approved_by_client",
        resource_type="content_item",
        resource_id=content.id,
        details={"from": previous.value, "to": content.status.value, "version_id": str(version.id)},
    )
    session.commit()
    return _serialize(session, content)


@router.post("/{content_id}/request-changes", response_model=ContentRead)
def request_changes(
    content_id: UUID,
    payload: ChangesRequest,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_role(context, *_CLIENT_REVIEWERS)
    content = _get_content(session, context, content_id)
    if context.membership.business_id != content.business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Revisão fora do cliente permitido")
    current = _get_current_version(session, content)
    approval = _pending_approval(session, content, current)
    previous = _transition(content, ContentStatus.CHANGES_REQUESTED)
    approval.status = ApprovalStatus.CHANGES_REQUESTED
    approval.decided_by_user_id = context.user.id
    approval.decision_comment = payload.comment.strip()
    from growthos.models.base import utcnow

    approval.decided_at = utcnow()
    new_version = ContentVersion(
        organization_id=content.organization_id,
        business_id=content.business_id,
        content_item_id=content.id,
        version_number=current.version_number + 1,
        title=current.title,
        caption=current.caption,
        channel=current.channel,
        format=current.format,
        objective=current.objective,
        audience=current.audience,
        cta=current.cta,
        provider_name="manual_revision",
        created_by_user_id=context.user.id,
    )
    session.add(new_version)
    session.flush()
    content.current_version_id = new_version.id
    _notify_agency(
        session,
        content,
        "Alteração solicitada",
        "O cliente pediu uma alteração no conteúdo.",
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
            "from": previous.value,
            "to": content.status.value,
            "reviewed_version_id": str(current.id),
            "new_version_id": str(new_version.id),
            "comment": payload.comment.strip(),
        },
    )
    session.commit()
    return _serialize(session, content)

