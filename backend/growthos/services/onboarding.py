from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from growthos.domain.enums import Role
from growthos.models import (
    AudienceSegment,
    BrandProfile,
    Business,
    BusinessOnboarding,
    MarketingObjective,
    MediaAsset,
    Membership,
    Service,
    User,
    VisualPreset,
)
from growthos.models.base import utcnow
from growthos.schemas_onboarding import (
    ApproversStep,
    AudiencesStep,
    BrandRulesStep,
    BusinessOnboardingRead,
    ColorsAndFontsStep,
    CompanyStep,
    DifferentiatorsStep,
    FinalReviewStep,
    InitialPresetStep,
    LogosStep,
    NotificationSettingsStep,
    ObjectivesStep,
    OnboardingStepPayload,
    OnboardingSummary,
    SegmentStep,
    ServicesStep,
    ToneOfVoiceStep,
    VisualReferencesStep,
)
from growthos.services.audit import add_audit_log

_CLIENT_APPROVER_ROLES = (Role.CLIENT_OWNER, Role.CLIENT_REVIEWER)
_ALL_STEPS = tuple(range(1, 16))


class OnboardingNotFoundError(LookupError):
    pass


class OnboardingResourceNotFoundError(LookupError):
    pass


class OnboardingConflictError(RuntimeError):
    pass


class OnboardingValidationError(ValueError):
    pass


def start_onboarding(
    session: Session,
    *,
    organization_id: UUID,
    actor_user_id: UUID,
    business: Business,
) -> BusinessOnboardingRead:
    onboarding = session.scalar(
        select(BusinessOnboarding)
        .where(
            BusinessOnboarding.organization_id == organization_id,
            BusinessOnboarding.business_id == business.id,
        )
        .with_for_update()
    )
    if onboarding is not None:
        return serialize_onboarding(session, onboarding, business)

    onboarding = BusinessOnboarding(
        organization_id=organization_id,
        business_id=business.id,
        status="IN_PROGRESS",
        current_step=1,
        completed_steps=[],
        step_data={},
        revision=1,
        started_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
    )
    session.add(onboarding)
    business.onboarding_status = "IN_PROGRESS"
    session.flush()
    add_audit_log(
        session,
        organization_id=organization_id,
        business_id=business.id,
        actor_user_id=actor_user_id,
        action="onboarding.started",
        resource_type="business_onboarding",
        resource_id=onboarding.id,
        details={"revision": onboarding.revision},
    )
    _commit(session, "O onboarding deste cliente já foi iniciado")
    return serialize_onboarding(session, onboarding, business)


def read_onboarding(
    session: Session,
    *,
    organization_id: UUID,
    business: Business,
) -> BusinessOnboardingRead:
    onboarding = _get_onboarding(session, organization_id, business.id)
    return serialize_onboarding(session, onboarding, business)


def save_onboarding_step(
    session: Session,
    *,
    organization_id: UUID,
    actor_user_id: UUID,
    business: Business,
    payload: OnboardingStepPayload,
) -> BusinessOnboardingRead:
    onboarding = _get_onboarding(session, organization_id, business.id, lock=True)
    if payload.revision != onboarding.revision:
        raise OnboardingConflictError(
            "O onboarding foi atualizado em outra sessão. Recarregue antes de continuar."
        )

    stored_data = _apply_step(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        business=business,
        payload=payload,
    )
    step_data = dict(onboarding.step_data)
    step_data[str(payload.step)] = stored_data
    completed_steps = set(onboarding.completed_steps)
    completed_steps.add(payload.step)
    onboarding.step_data = step_data
    onboarding.completed_steps = sorted(completed_steps)
    onboarding.current_step = max(onboarding.current_step, min(15, payload.step + 1))
    onboarding.updated_by_user_id = actor_user_id
    onboarding.revision += 1
    if onboarding.status != "COMPLETED":
        onboarding.status = "IN_PROGRESS"
        business.onboarding_status = "IN_PROGRESS"
    session.flush()
    add_audit_log(
        session,
        organization_id=organization_id,
        business_id=business.id,
        actor_user_id=actor_user_id,
        action="onboarding.step_saved",
        resource_type="business_onboarding",
        resource_id=onboarding.id,
        details={
            "step": payload.step,
            "revision": onboarding.revision,
            "current_step": onboarding.current_step,
        },
    )
    _commit(session, "Não foi possível salvar esta etapa do onboarding")
    return serialize_onboarding(session, onboarding, business)


def complete_onboarding(
    session: Session,
    *,
    organization_id: UUID,
    actor_user_id: UUID,
    business: Business,
    expected_revision: int,
) -> BusinessOnboardingRead:
    onboarding = _get_onboarding(session, organization_id, business.id, lock=True)
    if onboarding.status == "COMPLETED":
        return serialize_onboarding(session, onboarding, business)
    if expected_revision != onboarding.revision:
        raise OnboardingConflictError(
            "O onboarding foi atualizado em outra sessão. Recarregue antes de concluir."
        )
    missing_steps = _missing_steps(session, onboarding, business)
    if missing_steps:
        readable = ", ".join(str(step) for step in missing_steps)
        raise OnboardingConflictError(f"Conclua ou corrija as etapas: {readable}")

    completed_at = utcnow()
    onboarding.status = "COMPLETED"
    onboarding.current_step = 15
    onboarding.completed_steps = list(_ALL_STEPS)
    onboarding.completed_by_user_id = actor_user_id
    onboarding.updated_by_user_id = actor_user_id
    onboarding.completed_at = completed_at
    onboarding.revision += 1
    business.onboarding_status = "COMPLETED"
    business.onboarding_completed_at = completed_at
    add_audit_log(
        session,
        organization_id=organization_id,
        business_id=business.id,
        actor_user_id=actor_user_id,
        action="onboarding.completed",
        resource_type="business_onboarding",
        resource_id=onboarding.id,
        details={"revision": onboarding.revision, "steps": len(_ALL_STEPS)},
    )
    _commit(session, "Não foi possível concluir o onboarding")
    return serialize_onboarding(session, onboarding, business)


def serialize_onboarding(
    session: Session,
    onboarding: BusinessOnboarding,
    business: Business,
) -> BusinessOnboardingRead:
    summary = _summary(session, onboarding, business)
    completed_steps = sorted(step for step in set(onboarding.completed_steps) if step in _ALL_STEPS)
    return BusinessOnboardingRead(
        id=onboarding.id,
        organization_id=onboarding.organization_id,
        business_id=onboarding.business_id,
        status=onboarding.status,
        current_step=onboarding.current_step,
        completed_steps=completed_steps,
        missing_steps=_missing_steps(session, onboarding, business, summary=summary),
        progress_percent=round(len(completed_steps) * 100 / len(_ALL_STEPS)),
        revision=onboarding.revision,
        step_data=dict(onboarding.step_data),
        summary=summary,
        started_by_user_id=onboarding.started_by_user_id,
        updated_by_user_id=onboarding.updated_by_user_id,
        completed_by_user_id=onboarding.completed_by_user_id,
        completed_at=onboarding.completed_at,
        created_at=onboarding.created_at,
        updated_at=onboarding.updated_at,
    )


def _get_onboarding(
    session: Session,
    organization_id: UUID,
    business_id: UUID,
    *,
    lock: bool = False,
) -> BusinessOnboarding:
    query = select(BusinessOnboarding).where(
        BusinessOnboarding.organization_id == organization_id,
        BusinessOnboarding.business_id == business_id,
    )
    if lock:
        query = query.with_for_update()
    onboarding = session.scalar(query)
    if onboarding is None:
        raise OnboardingNotFoundError("Onboarding ainda não iniciado")
    return onboarding


def _apply_step(
    session: Session,
    *,
    organization_id: UUID,
    actor_user_id: UUID,
    business: Business,
    payload: OnboardingStepPayload,
) -> dict[str, Any]:
    if isinstance(payload, CompanyStep):
        business.name = payload.name
        business.timezone = payload.timezone
        brand = _brand_profile(session, organization_id, business, actor_user_id)
        brand.brand_name = payload.brand_name
        brand.public_name = payload.public_name
        brand.description = payload.description
        _touch_brand(brand)
    elif isinstance(payload, SegmentStep):
        business.segment = payload.segment
        brand = _brand_profile(session, organization_id, business, actor_user_id)
        brand.segment = payload.segment
        _touch_brand(brand)
    elif isinstance(payload, ServicesStep):
        ids = _upsert_services(session, organization_id, business.id, payload.services)
        brand = _brand_profile(session, organization_id, business, actor_user_id)
        brand.services = [item.name for item in payload.services]
        _touch_brand(brand)
        return {
            "services": [
                {
                    **item.model_dump(mode="json", exclude={"id"}),
                    "id": str(item_id),
                }
                for item, item_id in zip(payload.services, ids, strict=True)
            ]
        }
    elif isinstance(payload, AudiencesStep):
        ids = _upsert_audiences(session, organization_id, business.id, payload.audiences)
        brand = _brand_profile(session, organization_id, business, actor_user_id)
        brand.audience = "\n".join(item.name for item in payload.audiences)
        _touch_brand(brand)
        return {
            "audiences": [
                {
                    **item.model_dump(mode="json", exclude={"id"}),
                    "id": str(item_id),
                }
                for item, item_id in zip(payload.audiences, ids, strict=True)
            ]
        }
    elif isinstance(payload, ObjectivesStep):
        ids = _upsert_objectives(session, organization_id, business.id, payload.objectives)
        return {
            "objectives": [
                {
                    **item.model_dump(mode="json", exclude={"id"}),
                    "id": str(item_id),
                }
                for item, item_id in zip(payload.objectives, ids, strict=True)
            ]
        }
    elif isinstance(payload, DifferentiatorsStep):
        brand = _brand_profile(session, organization_id, business, actor_user_id)
        brand.differentiators = list(payload.differentiators)
        _touch_brand(brand)
    elif isinstance(payload, ToneOfVoiceStep):
        brand = _brand_profile(session, organization_id, business, actor_user_id)
        brand.tone_of_voice = payload.tone_of_voice
        brand.preferred_words = list(payload.preferred_words)
        brand.forbidden_words = list(payload.forbidden_words)
        _touch_brand(brand)
    elif isinstance(payload, LogosStep):
        _validate_media_assets(
            session,
            organization_id,
            business.id,
            payload.logo_media_asset_ids,
            label="Logo",
        )
        brand = _brand_profile(session, organization_id, business, actor_user_id)
        brand.logo_media_asset_ids = [str(asset_id) for asset_id in payload.logo_media_asset_ids]
        _touch_brand(brand)
    elif isinstance(payload, ColorsAndFontsStep):
        brand = _brand_profile(session, organization_id, business, actor_user_id)
        brand.primary_colors = list(payload.primary_colors)
        brand.secondary_colors = list(payload.secondary_colors)
        brand.fonts = list(payload.fonts)
        _touch_brand(brand)
    elif isinstance(payload, VisualReferencesStep):
        _validate_media_assets(
            session,
            organization_id,
            business.id,
            payload.visual_reference_media_asset_ids,
            label="Referência visual",
        )
        brand = _brand_profile(session, organization_id, business, actor_user_id)
        brand.visual_reference_media_asset_ids = [
            str(asset_id) for asset_id in payload.visual_reference_media_asset_ids
        ]
        _touch_brand(brand)
    elif isinstance(payload, BrandRulesStep):
        brand = _brand_profile(session, organization_id, business, actor_user_id)
        brand.allowed_rules = list(payload.allowed_rules)
        brand.forbidden_rules = list(payload.forbidden_rules)
        brand.required_terms = list(payload.required_terms)
        brand.legal_rules = list(payload.legal_rules)
        brand.image_restrictions = list(payload.image_restrictions)
        _touch_brand(brand)
    elif isinstance(payload, ApproversStep):
        _validate_approvers(
            session,
            organization_id,
            business.id,
            payload.membership_ids,
        )
    elif isinstance(payload, NotificationSettingsStep):
        # A preferência individual será materializada na fatia de notificações.
        # Aqui o onboarding preserva somente o rascunho estritamente validado.
        pass
    elif isinstance(payload, InitialPresetStep):
        preset_id = _resolve_initial_preset(
            session,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            business=business,
            payload=payload,
        )
        return {"preset_id": str(preset_id)}
    elif not isinstance(payload, FinalReviewStep):
        raise OnboardingValidationError("Etapa de onboarding desconhecida")

    return payload.model_dump(mode="json", exclude={"step", "revision"})


def _brand_profile(
    session: Session,
    organization_id: UUID,
    business: Business,
    actor_user_id: UUID,
) -> BrandProfile:
    brand = session.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == organization_id,
            BrandProfile.business_id == business.id,
        )
    )
    if brand is None:
        brand = BrandProfile(
            organization_id=organization_id,
            business_id=business.id,
            brand_name=business.name,
        )
        session.add(brand)
        session.flush()
    del actor_user_id  # reservado para autoria explícita quando o perfil ganhar esse campo
    return brand


def _touch_brand(brand: BrandProfile) -> None:
    brand.version += 1


def _upsert_services(
    session: Session,
    organization_id: UUID,
    business_id: UUID,
    items: Sequence[Any],
) -> list[UUID]:
    result: list[UUID] = []
    for payload in items:
        item = _catalog_item(
            session,
            Service,
            organization_id,
            business_id,
            payload.id,
            payload.name,
        )
        if item is None:
            item = Service(
                organization_id=organization_id,
                business_id=business_id,
                name=payload.name,
            )
            session.add(item)
        item.name = payload.name
        item.description = payload.description
        item.category = payload.category
        item.warnings = list(payload.warnings)
        item.is_active = True
        item.archived_at = None
        session.flush()
        result.append(item.id)
    return result


def _upsert_audiences(
    session: Session,
    organization_id: UUID,
    business_id: UUID,
    items: Sequence[Any],
) -> list[UUID]:
    result: list[UUID] = []
    for payload in items:
        item = _catalog_item(
            session,
            AudienceSegment,
            organization_id,
            business_id,
            payload.id,
            payload.name,
        )
        if item is None:
            item = AudienceSegment(
                organization_id=organization_id,
                business_id=business_id,
                name=payload.name,
            )
            session.add(item)
        item.name = payload.name
        item.description = payload.description
        item.needs = list(payload.needs)
        item.objections = list(payload.objections)
        item.location = payload.location
        item.is_active = True
        item.archived_at = None
        session.flush()
        result.append(item.id)
    return result


def _upsert_objectives(
    session: Session,
    organization_id: UUID,
    business_id: UUID,
    items: Sequence[Any],
) -> list[UUID]:
    result: list[UUID] = []
    for payload in items:
        item = _catalog_item(
            session,
            MarketingObjective,
            organization_id,
            business_id,
            payload.id,
            payload.name,
        )
        if item is None:
            item = MarketingObjective(
                organization_id=organization_id,
                business_id=business_id,
                name=payload.name,
            )
            session.add(item)
        item.name = payload.name
        item.description = payload.description
        item.planned_indicators = list(payload.planned_indicators)
        item.is_active = True
        item.archived_at = None
        session.flush()
        result.append(item.id)
    return result


def _catalog_item(
    session: Session,
    model: Any,
    organization_id: UUID,
    business_id: UUID,
    item_id: UUID | None,
    name: str,
) -> Any | None:
    if item_id is not None:
        item = session.scalar(
            select(model).where(
                model.id == item_id,
                model.organization_id == organization_id,
                model.business_id == business_id,
            )
        )
        if item is None:
            raise OnboardingResourceNotFoundError("Item de catálogo não encontrado")
        return item
    return session.scalar(
        select(model).where(
            model.organization_id == organization_id,
            model.business_id == business_id,
            model.name == name,
        )
    )


def _validate_media_assets(
    session: Session,
    organization_id: UUID,
    business_id: UUID,
    asset_ids: Sequence[UUID],
    *,
    label: str,
) -> None:
    found = set(
        session.scalars(
            select(MediaAsset.id).where(
                MediaAsset.id.in_(asset_ids),
                MediaAsset.organization_id == organization_id,
                MediaAsset.business_id == business_id,
                MediaAsset.processing_status == "READY",
                MediaAsset.archived_at.is_(None),
                MediaAsset.mime_type.like("image/%"),
            )
        ).all()
    )
    if found != set(asset_ids):
        raise OnboardingResourceNotFoundError(f"{label} não encontrado")


def _validate_approvers(
    session: Session,
    organization_id: UUID,
    business_id: UUID,
    membership_ids: Sequence[UUID],
) -> None:
    found = set(
        session.scalars(
            select(Membership.id)
            .join(User, User.id == Membership.user_id)
            .where(
                Membership.id.in_(membership_ids),
                Membership.organization_id == organization_id,
                Membership.business_id == business_id,
                Membership.role.in_(_CLIENT_APPROVER_ROLES),
                Membership.is_active.is_(True),
                User.is_active.is_(True),
            )
        ).all()
    )
    if found != set(membership_ids):
        raise OnboardingResourceNotFoundError("Responsável pela aprovação não encontrado")


def _resolve_initial_preset(
    session: Session,
    *,
    organization_id: UUID,
    actor_user_id: UUID,
    business: Business,
    payload: InitialPresetStep,
) -> UUID:
    brand = _brand_profile(session, organization_id, business, actor_user_id)
    if payload.preset_id is not None:
        preset = session.scalar(
            select(VisualPreset).where(
                VisualPreset.id == payload.preset_id,
                VisualPreset.organization_id == organization_id,
                VisualPreset.business_id == business.id,
                VisualPreset.brand_profile_id == brand.id,
                VisualPreset.is_active.is_(True),
            )
        )
        if preset is None:
            raise OnboardingResourceNotFoundError("Preset visual não encontrado")
        return preset.id

    preset_payload = payload.preset
    if preset_payload is None:
        raise OnboardingValidationError("Informe o preset visual inicial")
    if preset_payload.logo_media_asset_id is not None:
        _validate_media_assets(
            session,
            organization_id,
            business.id,
            [preset_payload.logo_media_asset_id],
            label="Logo do preset",
        )
    preset = session.scalar(
        select(VisualPreset).where(
            VisualPreset.organization_id == organization_id,
            VisualPreset.business_id == business.id,
            VisualPreset.name == preset_payload.name,
        )
    )
    values = preset_payload.model_dump()
    if preset is None:
        preset = VisualPreset(
            organization_id=organization_id,
            business_id=business.id,
            brand_profile_id=brand.id,
            created_by_user_id=actor_user_id,
            updated_by_user_id=actor_user_id,
            **values,
        )
        session.add(preset)
    else:
        if preset.brand_profile_id != brand.id:
            raise OnboardingConflictError("Preset visual inconsistente com o Brand Kit")
        for field, value in values.items():
            setattr(preset, field, value)
        preset.is_active = True
        preset.archived_at = None
        preset.updated_by_user_id = actor_user_id
        preset.version += 1
    session.flush()
    return preset.id


def _summary(
    session: Session,
    onboarding: BusinessOnboarding,
    business: Business,
) -> OnboardingSummary:
    organization_id = onboarding.organization_id
    business_id = business.id
    brand = session.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == organization_id,
            BrandProfile.business_id == business_id,
        )
    )
    service_ids = list(
        session.scalars(
            select(Service.id).where(
                Service.organization_id == organization_id,
                Service.business_id == business_id,
                Service.is_active.is_(True),
            )
        ).all()
    )
    audience_ids = list(
        session.scalars(
            select(AudienceSegment.id).where(
                AudienceSegment.organization_id == organization_id,
                AudienceSegment.business_id == business_id,
                AudienceSegment.is_active.is_(True),
            )
        ).all()
    )
    objective_ids = list(
        session.scalars(
            select(MarketingObjective.id).where(
                MarketingObjective.organization_id == organization_id,
                MarketingObjective.business_id == business_id,
                MarketingObjective.is_active.is_(True),
            )
        ).all()
    )
    step_data = onboarding.step_data
    approver_ids = _uuid_values(step_data.get("12", {}).get("membership_ids", []))
    preset_ids = _uuid_values([step_data.get("14", {}).get("preset_id")])
    return OnboardingSummary(
        business_id=business_id,
        brand_profile_id=brand.id if brand else None,
        service_ids=service_ids,
        audience_ids=audience_ids,
        objective_ids=objective_ids,
        logo_media_asset_ids=(
            _uuid_values(brand.logo_media_asset_ids) if brand is not None else []
        ),
        visual_reference_media_asset_ids=(
            _uuid_values(brand.visual_reference_media_asset_ids) if brand is not None else []
        ),
        approver_membership_ids=approver_ids,
        initial_preset_id=preset_ids[0] if preset_ids else None,
        notification_settings_configured="13" in step_data,
    )


def _missing_steps(
    session: Session,
    onboarding: BusinessOnboarding,
    business: Business,
    *,
    summary: OnboardingSummary | None = None,
) -> list[int]:
    summary = summary or _summary(session, onboarding, business)
    brand = None
    if summary.brand_profile_id is not None:
        brand = session.scalar(
            select(BrandProfile).where(
                BrandProfile.id == summary.brand_profile_id,
                BrandProfile.organization_id == onboarding.organization_id,
                BrandProfile.business_id == business.id,
            )
        )
    valid_media = _media_ids_are_valid(
        session,
        onboarding.organization_id,
        business.id,
        summary.logo_media_asset_ids + summary.visual_reference_media_asset_ids,
    )
    approvers_valid = _approver_ids_are_valid(
        session,
        onboarding.organization_id,
        business.id,
        summary.approver_membership_ids,
    )
    preset_valid = _preset_is_valid(
        session,
        onboarding.organization_id,
        business.id,
        summary.brand_profile_id,
        summary.initial_preset_id,
    )
    step_data = onboarding.step_data
    checks = {
        1: bool(business.name.strip() and business.timezone.strip() and brand and brand.brand_name),
        2: bool(business.segment.strip()),
        3: bool(summary.service_ids),
        4: bool(summary.audience_ids),
        5: bool(summary.objective_ids),
        6: bool(brand and brand.differentiators),
        7: bool(brand and brand.tone_of_voice.strip()),
        8: bool(summary.logo_media_asset_ids and valid_media),
        9: bool(brand and brand.primary_colors and brand.fonts),
        10: bool(summary.visual_reference_media_asset_ids and valid_media),
        11: bool(brand and brand.allowed_rules and brand.forbidden_rules),
        12: bool(summary.approver_membership_ids and approvers_valid),
        13: summary.notification_settings_configured,
        14: preset_valid,
        15: step_data.get("15", {}).get("confirmed") is True,
    }
    return [step for step in _ALL_STEPS if not checks[step]]


def _media_ids_are_valid(
    session: Session,
    organization_id: UUID,
    business_id: UUID,
    asset_ids: list[UUID],
) -> bool:
    if not asset_ids:
        return False
    found = set(
        session.scalars(
            select(MediaAsset.id).where(
                MediaAsset.id.in_(asset_ids),
                MediaAsset.organization_id == organization_id,
                MediaAsset.business_id == business_id,
                MediaAsset.processing_status == "READY",
                MediaAsset.archived_at.is_(None),
                MediaAsset.mime_type.like("image/%"),
            )
        ).all()
    )
    return found == set(asset_ids)


def _approver_ids_are_valid(
    session: Session,
    organization_id: UUID,
    business_id: UUID,
    membership_ids: list[UUID],
) -> bool:
    if not membership_ids:
        return False
    found = set(
        session.scalars(
            select(Membership.id)
            .join(User, User.id == Membership.user_id)
            .where(
                Membership.id.in_(membership_ids),
                Membership.organization_id == organization_id,
                Membership.business_id == business_id,
                Membership.role.in_(_CLIENT_APPROVER_ROLES),
                Membership.is_active.is_(True),
                User.is_active.is_(True),
            )
        ).all()
    )
    return found == set(membership_ids)


def _preset_is_valid(
    session: Session,
    organization_id: UUID,
    business_id: UUID,
    brand_profile_id: UUID | None,
    preset_id: UUID | None,
) -> bool:
    if preset_id is None or brand_profile_id is None:
        return False
    return (
        session.scalar(
            select(VisualPreset.id).where(
                VisualPreset.id == preset_id,
                VisualPreset.organization_id == organization_id,
                VisualPreset.business_id == business_id,
                VisualPreset.brand_profile_id == brand_profile_id,
                VisualPreset.is_active.is_(True),
            )
        )
        is not None
    )


def _uuid_values(values: Sequence[Any]) -> list[UUID]:
    result: list[UUID] = []
    for value in values:
        if value is None:
            continue
        try:
            result.append(UUID(str(value)))
        except (TypeError, ValueError):
            continue
    return result


def _commit(session: Session, message: str) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise OnboardingConflictError(message) from exc
