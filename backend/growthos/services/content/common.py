from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.domain.content import InvalidContentTransition, validate_transition
from growthos.domain.enums import ContentStatus
from growthos.models import BrandProfile, ContentItem, MediaAsset, VisualPreset


def transition(content: ContentItem, target: ContentStatus) -> ContentStatus:
    previous = content.status
    try:
        validate_transition(previous, target)
    except InvalidContentTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    content.status = target
    return previous


def get_scoped_visual_preset(
    session: Session,
    content: ContentItem,
    preset_id: UUID,
) -> tuple[VisualPreset, BrandProfile]:
    preset = session.scalar(
        select(VisualPreset).where(
            VisualPreset.id == preset_id,
            VisualPreset.organization_id == content.organization_id,
            VisualPreset.business_id == content.business_id,
            VisualPreset.is_active.is_(True),
            VisualPreset.archived_at.is_(None),
        )
    )
    if preset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Preset visual não encontrado")
    brand = session.scalar(
        select(BrandProfile).where(
            BrandProfile.id == preset.brand_profile_id,
            BrandProfile.organization_id == content.organization_id,
            BrandProfile.business_id == content.business_id,
        )
    )
    if brand is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Preset visual inconsistente")
    return preset, brand


def get_scoped_ready_image(
    session: Session,
    content: ContentItem,
    media_asset_id: UUID,
) -> MediaAsset:
    media_asset = session.scalar(
        select(MediaAsset).where(
            MediaAsset.id == media_asset_id,
            MediaAsset.organization_id == content.organization_id,
            MediaAsset.business_id == content.business_id,
            MediaAsset.mime_type.like("image/%"),
            MediaAsset.processing_status == "READY",
            MediaAsset.archived_at.is_(None),
        )
    )
    if media_asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mídia pronta não encontrada")
    return media_asset
