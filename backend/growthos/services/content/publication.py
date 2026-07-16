from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext
from growthos.domain.enums import ContentStatus
from growthos.models import CalendarEntry, ContentItem
from growthos.schemas import ContentRead, ManualPublicationCreate
from growthos.services.audit import add_audit_log
from growthos.services.content.common import transition
from growthos.services.content.read_models import (
    get_content,
    get_current_version,
    serialize_content,
)


def record_manual_publication(
    session: Session,
    context: AuthContext,
    content_id: UUID,
    payload: ManualPublicationCreate,
) -> ContentRead:
    content = get_content(session, context, content_id, for_update=True)
    idempotency_key = payload.idempotency_key.strip()
    channel = payload.channel.strip()
    if len(idempotency_key) < 8 or not channel:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Canal e chave de idempotência são obrigatórios",
        )
    if content.status == ContentStatus.PUBLISHED:
        if content.publication_idempotency_key == idempotency_key:
            return serialize_content(session, content, context)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este conteúdo já possui publicação manual registrada",
        )
    existing_content_id = session.scalar(
        select(ContentItem.id).where(
            ContentItem.organization_id == context.organization.id,
            ContentItem.publication_idempotency_key == idempotency_key,
        )
    )
    if existing_content_id is not None and existing_content_id != content.id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta chave de idempotência já foi utilizada",
        )
    if content.status not in {ContentStatus.APPROVED, ContentStatus.SCHEDULED}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Somente conteúdo aprovado ou agendado pode ser registrado como publicado",
        )
    calendar_entry: CalendarEntry | None = None
    if content.calendar_entry_id is not None:
        calendar_entry = session.scalar(
            select(CalendarEntry)
            .where(
                CalendarEntry.id == content.calendar_entry_id,
                CalendarEntry.organization_id == content.organization_id,
                CalendarEntry.business_id == content.business_id,
            )
            .with_for_update()
        )
        if calendar_entry is None or calendar_entry.content_item_id not in {None, content.id}:
            raise HTTPException(status.HTTP_409_CONFLICT, "Vínculo com calendário inconsistente")

    previous = content.status
    if content.status == ContentStatus.APPROVED:
        transition(content, ContentStatus.SCHEDULED)
    if content.scheduled_for is None:
        content.scheduled_for = payload.published_at
    transition(content, ContentStatus.PUBLISHED)
    content.published_at = payload.published_at
    content.publication_channel = channel
    content.publication_reference = payload.reference.strip() if payload.reference else None
    content.published_by_user_id = context.user.id
    content.publication_idempotency_key = idempotency_key
    if calendar_entry is not None:
        calendar_entry.content_item_id = content.id
        calendar_entry.status = "PUBLISHED"
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=content.business_id,
        actor_user_id=context.user.id,
        action="content.publication_recorded",
        resource_type="content_item",
        resource_id=content.id,
        details={
            "from": previous.value,
            "to": content.status.value,
            "version_id": str(get_current_version(session, content).id),
            "channel": channel,
            "published_at": payload.published_at.isoformat(),
            "has_reference": bool(content.publication_reference),
            "automatic_publication": False,
        },
    )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta chave de idempotência já foi utilizada",
        ) from exc
    return serialize_content(session, content, context)
