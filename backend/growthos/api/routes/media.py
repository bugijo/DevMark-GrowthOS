from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.config import Settings, get_settings
from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    get_scoped_business,
    require_capability,
    require_csrf,
)
from growthos.domain.permissions import Capability
from growthos.models import MediaAsset
from growthos.schemas_media import MediaAssetRead, SignedMediaUrlRead
from growthos.services.audit import add_audit_log
from growthos.services.storage import (
    InvalidUpload,
    StorageProvider,
    get_storage_provider,
    safe_display_name,
    validate_image_upload,
)

router = APIRouter()


def _scoped_asset(
    session: Session,
    context: AuthContext,
    asset_id: UUID,
) -> MediaAsset:
    asset = session.scalar(
        select(MediaAsset).where(
            MediaAsset.id == asset_id,
            MediaAsset.organization_id == context.organization.id,
            MediaAsset.archived_at.is_(None),
        )
    )
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo não encontrado")
    get_scoped_business(session, context, asset.business_id)
    return asset


@router.get("/businesses/{business_id}/media", response_model=list[MediaAssetRead])
def list_media(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[MediaAsset]:
    require_capability(context, Capability.MEDIA_VIEW)
    business = get_scoped_business(session, context, business_id)
    return list(
        session.scalars(
            select(MediaAsset)
            .where(
                MediaAsset.organization_id == context.organization.id,
                MediaAsset.business_id == business.id,
                MediaAsset.archived_at.is_(None),
                MediaAsset.processing_status == "READY",
            )
            .order_by(MediaAsset.created_at.desc())
        ).all()
    )


@router.post(
    "/businesses/{business_id}/media",
    response_model=MediaAssetRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    business_id: UUID,
    file: UploadFile = File(...),
    kind: str = Form(default="IMAGE"),
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    storage: StorageProvider = Depends(get_storage_provider),
) -> MediaAsset:
    require_capability(context, Capability.MEDIA_UPLOAD)
    business = get_scoped_business(session, context, business_id)
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    raw = await file.read(max_bytes + 1)
    await file.close()
    try:
        validated = validate_image_upload(
            raw,
            declared_mime=file.content_type,
            allowed_mime_types=settings.upload_mime_types,
            max_bytes=max_bytes,
        )
    except InvalidUpload as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    asset_id = uuid4()
    object_key = (
        f"organizations/{context.organization.id}/businesses/{business.id}/"
        f"media/{asset_id}.{validated.extension}"
    )
    storage.put(object_key, validated.data, validated.mime_type)
    asset = MediaAsset(
        id=asset_id,
        organization_id=context.organization.id,
        business_id=business.id,
        kind=kind.strip().upper()[:40] or "IMAGE",
        storage_provider=storage.name,
        object_key=object_key,
        display_name=safe_display_name(file.filename, validated.extension),
        mime_type=validated.mime_type,
        byte_size=validated.byte_size,
        checksum_sha256=validated.checksum_sha256,
        width=validated.width,
        height=validated.height,
        origin="UPLOAD",
        processing_status="READY",
        metadata_safe={},
        created_by_user_id=context.user.id,
    )
    session.add(asset)
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="media.uploaded",
        resource_type="media_asset",
        resource_id=asset.id,
        details={"mime_type": asset.mime_type, "byte_size": asset.byte_size},
    )
    try:
        session.commit()
    except Exception:
        storage.delete(object_key)
        raise
    return asset


@router.get("/media/{asset_id}/download-url", response_model=SignedMediaUrlRead)
def media_download_url(
    asset_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    storage: StorageProvider = Depends(get_storage_provider),
) -> SignedMediaUrlRead:
    require_capability(context, Capability.MEDIA_VIEW)
    asset = _scoped_asset(session, context, asset_id)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.signed_url_ttl_seconds)
    signed_url = storage.signed_get_url(asset.object_key, settings.signed_url_ttl_seconds)
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=asset.business_id,
        actor_user_id=context.user.id,
        action="media.signed_url_issued",
        resource_type="media_asset",
        resource_id=asset.id,
        details={"ttl_seconds": settings.signed_url_ttl_seconds},
    )
    session.commit()
    return SignedMediaUrlRead(
        url=signed_url,
        expires_at=expires_at,
    )


@router.delete("/media/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_media(
    asset_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> None:
    require_capability(context, Capability.MEDIA_MANAGE)
    asset = _scoped_asset(session, context, asset_id)
    asset.processing_status = "ARCHIVED"
    asset.archived_at = datetime.now(UTC)
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=asset.business_id,
        actor_user_id=context.user.id,
        action="media.archived",
        resource_type="media_asset",
        resource_id=asset.id,
    )
    session.commit()
