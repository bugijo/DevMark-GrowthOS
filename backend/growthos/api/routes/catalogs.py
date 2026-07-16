from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    get_scoped_business,
    require_capability,
    require_csrf,
)
from growthos.domain.enums import BUSINESS_SCOPED_ROLES
from growthos.domain.permissions import Capability
from growthos.models.base import utcnow
from growthos.models.business import BrandProfile
from growthos.models.catalog import (
    AudienceSegment,
    MarketingObjective,
    MediaAsset,
    Service,
    VisualPreset,
)
from growthos.schemas_catalog import (
    AudienceSegmentCreate,
    AudienceSegmentRead,
    AudienceSegmentUpdate,
    MarketingObjectiveCreate,
    MarketingObjectiveRead,
    MarketingObjectiveUpdate,
    ServiceCreate,
    ServiceRead,
    ServiceUpdate,
    VisualPresetCreate,
    VisualPresetRead,
    VisualPresetUpdate,
    VisualPromptGenerateRequest,
    VisualPromptRead,
)
from growthos.services.audit import add_audit_log
from growthos.services.visual_prompts import MockVisualPromptProvider, VisualPromptRequest

router = APIRouter()


def _serialize_visual_preset(
    preset: VisualPreset,
    context: AuthContext,
) -> VisualPresetRead:
    result = VisualPresetRead.model_validate(preset)
    if context.membership.role in BUSINESS_SCOPED_ROLES:
        return result.model_copy(
            update={
                "base_prompt": "",
                "negative_prompt": "",
                "created_by_user_id": None,
                "updated_by_user_id": None,
            }
        )
    return result


def _brand_profile(
    session: Session,
    context: AuthContext,
    business_id: UUID,
) -> BrandProfile:
    brand = session.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == context.organization.id,
            BrandProfile.business_id == business_id,
        )
    )
    if brand is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cadastre o Brand Kit antes de configurar o visual",
        )
    return brand


def _service(
    session: Session,
    context: AuthContext,
    business_id: UUID,
    service_id: UUID,
) -> Service:
    item = session.scalar(
        select(Service).where(
            Service.id == service_id,
            Service.organization_id == context.organization.id,
            Service.business_id == business_id,
            Service.is_active.is_(True),
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Serviço não encontrado")
    return item


def _audience(
    session: Session,
    context: AuthContext,
    business_id: UUID,
    audience_id: UUID,
) -> AudienceSegment:
    item = session.scalar(
        select(AudienceSegment).where(
            AudienceSegment.id == audience_id,
            AudienceSegment.organization_id == context.organization.id,
            AudienceSegment.business_id == business_id,
            AudienceSegment.is_active.is_(True),
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Público não encontrado")
    return item


def _objective(
    session: Session,
    context: AuthContext,
    business_id: UUID,
    objective_id: UUID,
) -> MarketingObjective:
    item = session.scalar(
        select(MarketingObjective).where(
            MarketingObjective.id == objective_id,
            MarketingObjective.organization_id == context.organization.id,
            MarketingObjective.business_id == business_id,
            MarketingObjective.is_active.is_(True),
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Objetivo não encontrado")
    return item


def _preset(
    session: Session,
    context: AuthContext,
    business_id: UUID,
    preset_id: UUID,
) -> VisualPreset:
    item = session.scalar(
        select(VisualPreset).where(
            VisualPreset.id == preset_id,
            VisualPreset.organization_id == context.organization.id,
            VisualPreset.business_id == business_id,
            VisualPreset.is_active.is_(True),
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Preset visual não encontrado")
    return item


def _validate_logo_asset(
    session: Session,
    context: AuthContext,
    business_id: UUID,
    media_asset_id: UUID | None,
) -> None:
    if media_asset_id is None:
        return
    exists = session.scalar(
        select(MediaAsset.id).where(
            MediaAsset.id == media_asset_id,
            MediaAsset.organization_id == context.organization.id,
            MediaAsset.business_id == business_id,
            MediaAsset.archived_at.is_(None),
            MediaAsset.processing_status == "READY",
        )
    )
    if exists is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Logo não encontrado")


def _commit_unique(session: Session, message: str) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, message) from exc


def _apply_changes(item: object, changes: dict[str, Any]) -> None:
    for field, value in changes.items():
        setattr(item, field, value)


@router.get(
    "/businesses/{business_id}/services",
    response_model=list[ServiceRead],
)
def list_services(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[Service]:
    require_capability(context, Capability.BRAND_VIEW)
    get_scoped_business(session, context, business_id)
    return list(
        session.scalars(
            select(Service)
            .where(
                Service.organization_id == context.organization.id,
                Service.business_id == business_id,
                Service.is_active.is_(True),
            )
            .order_by(Service.name)
        ).all()
    )


@router.post(
    "/businesses/{business_id}/services",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_service(
    business_id: UUID,
    payload: ServiceCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> Service:
    require_capability(context, Capability.SERVICE_MANAGE)
    get_scoped_business(session, context, business_id)
    item = Service(
        organization_id=context.organization.id,
        business_id=business_id,
        name=payload.name,
        description=payload.description,
        category=payload.category or "",
        warnings=payload.warnings,
    )
    session.add(item)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um serviço com este nome") from exc
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business_id,
        actor_user_id=context.user.id,
        action="service.created",
        resource_type="service",
        resource_id=item.id,
        details={"name": item.name},
    )
    session.commit()
    session.refresh(item)
    return item


@router.get(
    "/businesses/{business_id}/services/{service_id}",
    response_model=ServiceRead,
)
def get_service(
    business_id: UUID,
    service_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> Service:
    require_capability(context, Capability.BRAND_VIEW)
    get_scoped_business(session, context, business_id)
    return _service(session, context, business_id, service_id)


@router.patch(
    "/businesses/{business_id}/services/{service_id}",
    response_model=ServiceRead,
)
def update_service(
    business_id: UUID,
    service_id: UUID,
    payload: ServiceUpdate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> Service:
    require_capability(context, Capability.SERVICE_MANAGE)
    get_scoped_business(session, context, business_id)
    item = _service(session, context, business_id, service_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("category") is None and "category" in changes:
        changes["category"] = ""
    _apply_changes(item, changes)
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business_id,
        actor_user_id=context.user.id,
        action="service.updated",
        resource_type="service",
        resource_id=item.id,
        details={"fields": sorted(changes)},
    )
    _commit_unique(session, "Já existe um serviço com este nome")
    return item


@router.delete(
    "/businesses/{business_id}/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def archive_service(
    business_id: UUID,
    service_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> None:
    require_capability(context, Capability.SERVICE_MANAGE)
    get_scoped_business(session, context, business_id)
    item = _service(session, context, business_id, service_id)
    item.is_active = False
    item.archived_at = utcnow()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business_id,
        actor_user_id=context.user.id,
        action="service.archived",
        resource_type="service",
        resource_id=item.id,
    )
    session.commit()


@router.get(
    "/businesses/{business_id}/audiences",
    response_model=list[AudienceSegmentRead],
)
def list_audiences(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[AudienceSegment]:
    require_capability(context, Capability.BRAND_VIEW)
    get_scoped_business(session, context, business_id)
    return list(
        session.scalars(
            select(AudienceSegment)
            .where(
                AudienceSegment.organization_id == context.organization.id,
                AudienceSegment.business_id == business_id,
                AudienceSegment.is_active.is_(True),
            )
            .order_by(AudienceSegment.name)
        ).all()
    )


@router.post(
    "/businesses/{business_id}/audiences",
    response_model=AudienceSegmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_audience(
    business_id: UUID,
    payload: AudienceSegmentCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> AudienceSegment:
    require_capability(context, Capability.AUDIENCE_MANAGE)
    get_scoped_business(session, context, business_id)
    item = AudienceSegment(
        organization_id=context.organization.id,
        business_id=business_id,
        name=payload.name,
        description=payload.description,
        needs=payload.needs,
        objections=payload.objections,
        location=payload.location or "",
    )
    session.add(item)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um público com este nome") from exc
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business_id,
        actor_user_id=context.user.id,
        action="audience_segment.created",
        resource_type="audience_segment",
        resource_id=item.id,
        details={"name": item.name},
    )
    session.commit()
    session.refresh(item)
    return item


@router.get(
    "/businesses/{business_id}/audiences/{audience_id}",
    response_model=AudienceSegmentRead,
)
def get_audience(
    business_id: UUID,
    audience_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> AudienceSegment:
    require_capability(context, Capability.BRAND_VIEW)
    get_scoped_business(session, context, business_id)
    return _audience(session, context, business_id, audience_id)


@router.patch(
    "/businesses/{business_id}/audiences/{audience_id}",
    response_model=AudienceSegmentRead,
)
def update_audience(
    business_id: UUID,
    audience_id: UUID,
    payload: AudienceSegmentUpdate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> AudienceSegment:
    require_capability(context, Capability.AUDIENCE_MANAGE)
    get_scoped_business(session, context, business_id)
    item = _audience(session, context, business_id, audience_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("location") is None and "location" in changes:
        changes["location"] = ""
    _apply_changes(item, changes)
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business_id,
        actor_user_id=context.user.id,
        action="audience_segment.updated",
        resource_type="audience_segment",
        resource_id=item.id,
        details={"fields": sorted(changes)},
    )
    _commit_unique(session, "Já existe um público com este nome")
    return item


@router.delete(
    "/businesses/{business_id}/audiences/{audience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def archive_audience(
    business_id: UUID,
    audience_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> None:
    require_capability(context, Capability.AUDIENCE_MANAGE)
    get_scoped_business(session, context, business_id)
    item = _audience(session, context, business_id, audience_id)
    item.is_active = False
    item.archived_at = utcnow()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business_id,
        actor_user_id=context.user.id,
        action="audience_segment.archived",
        resource_type="audience_segment",
        resource_id=item.id,
    )
    session.commit()


@router.get(
    "/businesses/{business_id}/objectives",
    response_model=list[MarketingObjectiveRead],
)
def list_objectives(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[MarketingObjective]:
    require_capability(context, Capability.BRAND_VIEW)
    get_scoped_business(session, context, business_id)
    return list(
        session.scalars(
            select(MarketingObjective)
            .where(
                MarketingObjective.organization_id == context.organization.id,
                MarketingObjective.business_id == business_id,
                MarketingObjective.is_active.is_(True),
            )
            .order_by(MarketingObjective.name)
        ).all()
    )


@router.post(
    "/businesses/{business_id}/objectives",
    response_model=MarketingObjectiveRead,
    status_code=status.HTTP_201_CREATED,
)
def create_objective(
    business_id: UUID,
    payload: MarketingObjectiveCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> MarketingObjective:
    require_capability(context, Capability.OBJECTIVE_MANAGE)
    get_scoped_business(session, context, business_id)
    item = MarketingObjective(
        organization_id=context.organization.id,
        business_id=business_id,
        name=payload.name,
        description=payload.description,
        planned_indicators=payload.planned_indicators,
    )
    session.add(item)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Já existe um objetivo com este nome",
        ) from exc
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business_id,
        actor_user_id=context.user.id,
        action="marketing_objective.created",
        resource_type="marketing_objective",
        resource_id=item.id,
        details={"name": item.name},
    )
    session.commit()
    session.refresh(item)
    return item


@router.get(
    "/businesses/{business_id}/objectives/{objective_id}",
    response_model=MarketingObjectiveRead,
)
def get_objective(
    business_id: UUID,
    objective_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> MarketingObjective:
    require_capability(context, Capability.BRAND_VIEW)
    get_scoped_business(session, context, business_id)
    return _objective(session, context, business_id, objective_id)


@router.patch(
    "/businesses/{business_id}/objectives/{objective_id}",
    response_model=MarketingObjectiveRead,
)
def update_objective(
    business_id: UUID,
    objective_id: UUID,
    payload: MarketingObjectiveUpdate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> MarketingObjective:
    require_capability(context, Capability.OBJECTIVE_MANAGE)
    get_scoped_business(session, context, business_id)
    item = _objective(session, context, business_id, objective_id)
    changes = payload.model_dump(exclude_unset=True)
    _apply_changes(item, changes)
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business_id,
        actor_user_id=context.user.id,
        action="marketing_objective.updated",
        resource_type="marketing_objective",
        resource_id=item.id,
        details={"fields": sorted(changes)},
    )
    _commit_unique(session, "Já existe um objetivo com este nome")
    return item


@router.delete(
    "/businesses/{business_id}/objectives/{objective_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def archive_objective(
    business_id: UUID,
    objective_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> None:
    require_capability(context, Capability.OBJECTIVE_MANAGE)
    get_scoped_business(session, context, business_id)
    item = _objective(session, context, business_id, objective_id)
    item.is_active = False
    item.archived_at = utcnow()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business_id,
        actor_user_id=context.user.id,
        action="marketing_objective.archived",
        resource_type="marketing_objective",
        resource_id=item.id,
    )
    session.commit()


@router.get(
    "/businesses/{business_id}/visual-presets",
    response_model=list[VisualPresetRead],
)
def list_visual_presets(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[VisualPresetRead]:
    require_capability(context, Capability.PRESET_VIEW)
    get_scoped_business(session, context, business_id)
    presets = list(
        session.scalars(
            select(VisualPreset)
            .where(
                VisualPreset.organization_id == context.organization.id,
                VisualPreset.business_id == business_id,
                VisualPreset.is_active.is_(True),
            )
            .order_by(VisualPreset.name)
        ).all()
    )
    return [_serialize_visual_preset(preset, context) for preset in presets]


@router.post(
    "/businesses/{business_id}/visual-presets",
    response_model=VisualPresetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_visual_preset(
    business_id: UUID,
    payload: VisualPresetCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> VisualPresetRead:
    require_capability(context, Capability.PRESET_MANAGE)
    get_scoped_business(session, context, business_id)
    brand = _brand_profile(session, context, business_id)
    _validate_logo_asset(session, context, business_id, payload.logo_media_asset_id)
    item = VisualPreset(
        organization_id=context.organization.id,
        business_id=business_id,
        brand_profile_id=brand.id,
        created_by_user_id=context.user.id,
        updated_by_user_id=context.user.id,
        **payload.model_dump(),
    )
    session.add(item)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um preset com este nome") from exc
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business_id,
        actor_user_id=context.user.id,
        action="visual_preset.created",
        resource_type="visual_preset",
        resource_id=item.id,
        details={"name": item.name, "mode": item.creation_mode, "version": item.version},
    )
    session.commit()
    session.refresh(item)
    return _serialize_visual_preset(item, context)


@router.get(
    "/businesses/{business_id}/visual-presets/{preset_id}",
    response_model=VisualPresetRead,
)
def get_visual_preset(
    business_id: UUID,
    preset_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> VisualPresetRead:
    require_capability(context, Capability.PRESET_VIEW)
    get_scoped_business(session, context, business_id)
    item = _preset(session, context, business_id, preset_id)
    brand = _brand_profile(session, context, business_id)
    if item.brand_profile_id != brand.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Preset visual inconsistente")
    _validate_logo_asset(session, context, business_id, item.logo_media_asset_id)
    return _serialize_visual_preset(item, context)


@router.patch(
    "/businesses/{business_id}/visual-presets/{preset_id}",
    response_model=VisualPresetRead,
)
def update_visual_preset(
    business_id: UUID,
    preset_id: UUID,
    payload: VisualPresetUpdate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> VisualPreset:
    require_capability(context, Capability.PRESET_MANAGE)
    get_scoped_business(session, context, business_id)
    brand = _brand_profile(session, context, business_id)
    item = _preset(session, context, business_id, preset_id)
    if item.brand_profile_id != brand.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Preset visual inconsistente")
    changes = payload.model_dump(exclude_unset=True)
    if "logo_media_asset_id" in changes:
        _validate_logo_asset(session, context, business_id, changes["logo_media_asset_id"])
    _apply_changes(item, changes)
    _validate_logo_asset(session, context, business_id, item.logo_media_asset_id)
    item.version += 1
    item.updated_by_user_id = context.user.id
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business_id,
        actor_user_id=context.user.id,
        action="visual_preset.updated",
        resource_type="visual_preset",
        resource_id=item.id,
        details={"fields": sorted(changes), "version": item.version},
    )
    _commit_unique(session, "Já existe um preset com este nome")
    return item


@router.delete(
    "/businesses/{business_id}/visual-presets/{preset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def archive_visual_preset(
    business_id: UUID,
    preset_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> None:
    require_capability(context, Capability.PRESET_MANAGE)
    get_scoped_business(session, context, business_id)
    item = _preset(session, context, business_id, preset_id)
    item.is_active = False
    item.archived_at = utcnow()
    item.updated_by_user_id = context.user.id
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business_id,
        actor_user_id=context.user.id,
        action="visual_preset.archived",
        resource_type="visual_preset",
        resource_id=item.id,
        details={"version": item.version},
    )
    session.commit()


@router.post("/visual-prompts/generate", response_model=VisualPromptRead)
def generate_visual_prompt(
    payload: VisualPromptGenerateRequest,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> VisualPromptRead:
    require_capability(context, Capability.VISUAL_PROMPT_GENERATE)
    get_scoped_business(session, context, payload.business_id)
    brand = _brand_profile(session, context, payload.business_id)
    preset = _preset(session, context, payload.business_id, payload.preset_id)
    if preset.brand_profile_id != brand.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Preset visual inconsistente")
    _validate_logo_asset(
        session,
        context,
        payload.business_id,
        preset.logo_media_asset_id,
    )
    try:
        result = MockVisualPromptProvider().generate(
            VisualPromptRequest(
                brand_name=brand.brand_name,
                objective=payload.objective,
                audience=payload.audience or brand.audience,
                format=payload.format or preset.format,
                aspect_ratio=payload.aspect_ratio or preset.aspect_ratio,
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
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Preset visual inconsistente") from exc
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=payload.business_id,
        actor_user_id=context.user.id,
        action="visual_prompt.generated",
        resource_type="visual_preset",
        resource_id=preset.id,
        details={
            "provider": result.provider_name,
            "provider_reference": result.provider_reference,
            "preset_version": preset.version,
        },
    )
    session.commit()
    return VisualPromptRead(
        business_id=payload.business_id,
        preset_id=preset.id,
        preset_version=preset.version,
        prompt=result.prompt,
        negative_prompt=result.negative_prompt,
        provider_name=result.provider_name,
        provider_reference=result.provider_reference,
    )
