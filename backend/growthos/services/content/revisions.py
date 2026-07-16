from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext
from growthos.domain.enums import ContentStatus
from growthos.models import ContentVersion, ContentVersionMedia
from growthos.schemas import ContentRead, ContentRevisionCreate, ContentVisualRevisionCreate
from growthos.services.audit import add_audit_log
from growthos.services.content.common import (
    get_scoped_ready_image,
    get_scoped_visual_preset,
    transition,
)
from growthos.services.content.read_models import (
    get_content,
    get_current_version,
    serialize_content,
)
from growthos.services.content.snapshots import preset_snapshot
from growthos.services.visual_prompts import MockVisualPromptProvider, VisualPromptRequest


def create_revision(
    session: Session,
    context: AuthContext,
    content_id: UUID,
    payload: ContentRevisionCreate,
) -> ContentRead:
    content = get_content(session, context, content_id, for_update=True)
    current = get_current_version(session, content)
    title = payload.title.strip()
    caption = payload.caption.strip()
    cta = payload.cta.strip()
    notes = payload.notes.strip() if payload.notes is not None else current.notes
    script = payload.script.strip() if payload.script is not None else current.script
    if not title or not caption:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Título e legenda não podem ficar vazios",
        )
    if (title, caption, cta, notes, script) == (
        current.title,
        current.caption,
        current.cta,
        current.notes,
        current.script,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Altere ao menos um campo antes de criar uma nova versão",
        )

    previous = transition(content, ContentStatus.DRAFT)
    new_version = ContentVersion(
        organization_id=content.organization_id,
        business_id=content.business_id,
        content_item_id=content.id,
        version_number=current.version_number + 1,
        title=title,
        caption=caption,
        channel=current.channel,
        format=current.format,
        objective=current.objective,
        audience=current.audience,
        cta=cta,
        service_id=current.service_id,
        audience_segment_id=current.audience_segment_id,
        marketing_objective_id=current.marketing_objective_id,
        notes=notes,
        script=script,
        visual_prompt=current.visual_prompt,
        negative_prompt=current.negative_prompt,
        brand_context_snapshot=dict(current.brand_context_snapshot),
        visual_preset_snapshot=dict(current.visual_preset_snapshot),
        provider_name="manual_revision",
        created_by_user_id=context.user.id,
    )
    session.add(new_version)
    session.flush()
    previous_media = list(
        session.scalars(
            select(ContentVersionMedia).where(
                ContentVersionMedia.organization_id == content.organization_id,
                ContentVersionMedia.business_id == content.business_id,
                ContentVersionMedia.content_version_id == current.id,
            )
        ).all()
    )
    for association in previous_media:
        session.add(
            ContentVersionMedia(
                organization_id=content.organization_id,
                business_id=content.business_id,
                content_version_id=new_version.id,
                media_asset_id=association.media_asset_id,
                role=association.role,
                sort_order=association.sort_order,
                created_by_user_id=context.user.id,
            )
        )
    content.current_version_id = new_version.id
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=content.business_id,
        actor_user_id=context.user.id,
        action="content.revision_created",
        resource_type="content_item",
        resource_id=content.id,
        details={
            "from": previous.value,
            "to": content.status.value,
            "previous_version_id": str(current.id),
            "new_version_id": str(new_version.id),
            "version": new_version.version_number,
        },
    )
    session.commit()
    return serialize_content(session, content, context)


def create_visual_revision(
    session: Session,
    context: AuthContext,
    content_id: UUID,
    payload: ContentVisualRevisionCreate,
) -> ContentRead:
    content = get_content(session, context, content_id, for_update=True)
    current = get_current_version(session, content)
    fields = payload.model_fields_set

    old_preset_id = content.visual_preset_id
    new_preset_id = old_preset_id
    visual_prompt = current.visual_prompt
    negative_prompt = current.negative_prompt
    visual_preset_snapshot = dict(current.visual_preset_snapshot)
    prompt_source = "carried"

    if "visual_preset_id" in fields:
        new_preset_id = payload.visual_preset_id
        if new_preset_id is None:
            visual_preset_snapshot = {}
            visual_prompt = ""
            negative_prompt = ""
            prompt_source = "cleared"
        else:
            preset, brand = get_scoped_visual_preset(session, content, new_preset_id)
            result = MockVisualPromptProvider().generate(
                VisualPromptRequest(
                    brand_name=brand.brand_name,
                    objective=current.objective,
                    audience=current.audience,
                    format=preset.format,
                    aspect_ratio=preset.aspect_ratio,
                    creation_mode=preset.creation_mode,
                    tone_of_voice=brand.tone_of_voice,
                    base_prompt=preset.base_prompt,
                    negative_prompt=preset.negative_prompt,
                    background_style=preset.background_style,
                    photographic_style=preset.photographic_style,
                    lighting=preset.lighting,
                    composition=preset.composition,
                    realism_level=preset.realism_level,
                    allowed_elements=tuple(preset.allowed_elements),
                    forbidden_elements=tuple(preset.forbidden_elements),
                )
            )
            visual_prompt = result.prompt
            negative_prompt = result.negative_prompt
            visual_preset_snapshot = preset_snapshot(preset)
            visual_preset_snapshot["prompt_provider"] = result.provider_name
            visual_preset_snapshot["prompt_provider_reference"] = result.provider_reference
            prompt_source = "mock"

    has_manual_prompt = bool({"visual_prompt", "negative_prompt"}.intersection(fields))
    if "visual_prompt" in fields:
        visual_prompt = (payload.visual_prompt or "").strip()
    if "negative_prompt" in fields:
        negative_prompt = (payload.negative_prompt or "").strip()
    if has_manual_prompt:
        prompt_source = "manual" if prompt_source == "carried" else f"{prompt_source}_manual"

    previous_media = list(
        session.scalars(
            select(ContentVersionMedia)
            .where(
                ContentVersionMedia.organization_id == content.organization_id,
                ContentVersionMedia.business_id == content.business_id,
                ContentVersionMedia.content_version_id == current.id,
            )
            .order_by(ContentVersionMedia.sort_order, ContentVersionMedia.created_at)
        ).all()
    )
    next_media: list[tuple[UUID, str, int]]
    if "media_asset_id" not in fields:
        next_media = [
            (association.media_asset_id, association.role, association.sort_order)
            for association in previous_media
        ]
    elif payload.media_asset_id is None:
        next_media = []
    else:
        media_asset = get_scoped_ready_image(session, content, payload.media_asset_id)
        next_media = [(media_asset.id, "PRIMARY", 0)]

    old_media = [
        (association.media_asset_id, association.role, association.sort_order)
        for association in previous_media
    ]
    if (
        new_preset_id == old_preset_id
        and visual_prompt == current.visual_prompt
        and negative_prompt == current.negative_prompt
        and visual_preset_snapshot == current.visual_preset_snapshot
        and next_media == old_media
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Altere ao menos um elemento visual antes de criar uma nova versão",
        )

    previous_status = transition(content, ContentStatus.DRAFT)
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
        service_id=current.service_id,
        audience_segment_id=current.audience_segment_id,
        marketing_objective_id=current.marketing_objective_id,
        notes=current.notes,
        script=current.script,
        visual_prompt=visual_prompt,
        negative_prompt=negative_prompt,
        brand_context_snapshot=dict(current.brand_context_snapshot),
        visual_preset_snapshot=visual_preset_snapshot,
        provider_name=(
            "mock_visual_revision" if prompt_source.startswith("mock") else "manual_visual_revision"
        ),
        created_by_user_id=context.user.id,
    )
    session.add(new_version)
    session.flush()
    for media_asset_id, role, sort_order in next_media:
        session.add(
            ContentVersionMedia(
                organization_id=content.organization_id,
                business_id=content.business_id,
                content_version_id=new_version.id,
                media_asset_id=media_asset_id,
                role=role,
                sort_order=sort_order,
                created_by_user_id=context.user.id,
            )
        )
    content.current_version_id = new_version.id
    content.visual_preset_id = new_preset_id
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=content.business_id,
        actor_user_id=context.user.id,
        action="content.visual_revision_created",
        resource_type="content_item",
        resource_id=content.id,
        details={
            "from": previous_status.value,
            "to": content.status.value,
            "previous_version_id": str(current.id),
            "new_version_id": str(new_version.id),
            "version": new_version.version_number,
            "visual_preset_id": str(new_preset_id) if new_preset_id else None,
            "media_asset_ids": [str(media_id) for media_id, _, _ in next_media],
            "prompt_source": prompt_source,
        },
    )
    session.commit()
    return serialize_content(session, content, context)
