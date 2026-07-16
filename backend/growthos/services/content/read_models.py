from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext, get_scoped_business
from growthos.domain.enums import (
    ApprovalStage,
    ApprovalStatus,
    ContentStatus,
    Role,
)
from growthos.models import Approval, Business, ContentItem, ContentVersion, ContentVersionMedia
from growthos.schemas import ApprovalRead, ContentRead, ContentVersionRead

_BUSINESS_PORTAL_ROLES = frozenset({Role.CLIENT_OWNER, Role.CLIENT_REVIEWER, Role.VIEWER})
# Estes estados comprovam que o item atravessou a liberação para o portal. FAILED e
# ARCHIVED ficam de fora porque também podem ser alcançados antes da revisão do cliente.
_CLIENT_VISIBLE_STATUSES = (
    ContentStatus.CLIENT_REVIEW,
    ContentStatus.CHANGES_REQUESTED,
    ContentStatus.APPROVED,
    ContentStatus.SCHEDULED,
    ContentStatus.PUBLISHED,
)


def is_business_portal_context(context: AuthContext) -> bool:
    return context.membership.role in _BUSINESS_PORTAL_ROLES


def get_content(
    session: Session,
    context: AuthContext,
    content_id: UUID,
    *,
    for_update: bool = False,
) -> ContentItem:
    query = (
        select(ContentItem)
        .join(Business, Business.id == ContentItem.business_id)
        .where(
            ContentItem.id == content_id,
            ContentItem.organization_id == context.organization.id,
            Business.organization_id == context.organization.id,
            Business.is_active.is_(True),
        )
    )
    limited_business = context.membership.business_id
    if is_business_portal_context(context):
        if limited_business is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conteúdo não encontrado")
        query = query.where(
            ContentItem.business_id == limited_business,
            ContentItem.status.in_(_CLIENT_VISIBLE_STATUSES),
        )
    elif limited_business is not None:
        query = query.where(ContentItem.business_id == limited_business)
    if for_update:
        query = query.with_for_update()
    content = session.scalar(query)
    if content is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conteúdo não encontrado")
    return content


def get_current_version(session: Session, content: ContentItem) -> ContentVersion:
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


def serialize_content(
    session: Session,
    content: ContentItem,
    context: AuthContext,
) -> ContentRead:
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
            )
            .order_by(Approval.component)
        ).all()
    )
    media_asset_ids = list(
        session.scalars(
            select(ContentVersionMedia.media_asset_id)
            .where(
                ContentVersionMedia.organization_id == content.organization_id,
                ContentVersionMedia.business_id == content.business_id,
                ContentVersionMedia.content_version_id == version.id,
            )
            .order_by(ContentVersionMedia.sort_order, ContentVersionMedia.created_at)
        ).all()
    )
    change_request_comment: str | None = None
    if content.status == ContentStatus.CHANGES_REQUESTED:
        change_request_comment = session.scalar(
            select(Approval.decision_comment)
            .where(
                Approval.organization_id == content.organization_id,
                Approval.business_id == content.business_id,
                Approval.content_item_id == content.id,
                Approval.status == ApprovalStatus.CHANGES_REQUESTED,
            )
            .order_by(Approval.decided_at.desc())
            .limit(1)
        )
    version_read = ContentVersionRead.model_validate(version).model_copy(
        update={"media_asset_ids": media_asset_ids}
    )
    approval_reads = [ApprovalRead.model_validate(approval) for approval in approvals]
    published_by_user_id = content.published_by_user_id
    if is_business_portal_context(context):
        version_read = version_read.model_copy(
            update={
                "notes": "",
                "visual_prompt": "",
                "negative_prompt": "",
                "brand_context_snapshot": {},
                "visual_preset_snapshot": {},
            }
        )
        approval_reads = [
            approval.model_copy(update={"requested_by_user_id": None, "decided_by_user_id": None})
            for approval in approval_reads
        ]
        published_by_user_id = None
    return ContentRead(
        id=content.id,
        organization_id=content.organization_id,
        business_id=content.business_id,
        status=content.status,
        content_strategy_id=content.content_strategy_id,
        strategy_version_id=content.strategy_version_id,
        content_plan_id=content.content_plan_id,
        calendar_entry_id=content.calendar_entry_id,
        visual_preset_id=content.visual_preset_id,
        scheduled_for=content.scheduled_for,
        published_at=content.published_at,
        publication_channel=content.publication_channel,
        publication_reference=content.publication_reference,
        published_by_user_id=published_by_user_id,
        change_request_comment=change_request_comment,
        current_version=version_read,
        approvals=approval_reads,
        created_at=content.created_at,
        updated_at=content.updated_at,
    )


def list_contents(
    session: Session,
    context: AuthContext,
    business_id: UUID | None,
) -> list[ContentRead]:
    query = (
        select(ContentItem)
        .join(Business, Business.id == ContentItem.business_id)
        .where(
            ContentItem.organization_id == context.organization.id,
            Business.organization_id == context.organization.id,
            Business.is_active.is_(True),
        )
    )
    limited_business = context.membership.business_id
    if is_business_portal_context(context):
        if limited_business is None:
            return []
        if business_id is not None and business_id != limited_business:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
        query = query.where(
            ContentItem.business_id == limited_business,
            ContentItem.status.in_(_CLIENT_VISIBLE_STATUSES),
        )
    elif limited_business is not None:
        if business_id is not None and business_id != limited_business:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
        query = query.where(ContentItem.business_id == limited_business)
    elif business_id is not None:
        get_scoped_business(session, context, business_id)
        query = query.where(ContentItem.business_id == business_id)
    contents = session.scalars(query.order_by(ContentItem.created_at.desc())).all()
    return [serialize_content(session, content, context) for content in contents]
