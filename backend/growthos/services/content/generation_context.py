from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext
from growthos.models import (
    AudienceSegment,
    BrandProfile,
    CalendarEntry,
    ContentPlan,
    ContentStrategy,
    MarketingObjective,
    MediaAsset,
    Service,
    StrategyVersion,
    VisualPreset,
)
from growthos.schemas import ContentGenerateRequest


@dataclass(frozen=True)
class GenerationLinks:
    strategy: ContentStrategy | None
    strategy_version: StrategyVersion | None
    plan: ContentPlan | None
    calendar_entry: CalendarEntry | None
    preset: VisualPreset | None
    service: Service | None
    audience: AudienceSegment | None
    marketing_objective: MarketingObjective | None
    media_asset: MediaAsset | None


def resolve_generation_links(
    session: Session,
    context: AuthContext,
    payload: ContentGenerateRequest,
    brand: BrandProfile | None,
) -> GenerationLinks:
    organization_id = context.organization.id
    business_id = payload.business_id
    strategy_id = payload.content_strategy_id
    strategy_version_id = payload.strategy_version_id
    plan_id = payload.content_plan_id
    preset_id = payload.visual_preset_id

    calendar_entry: CalendarEntry | None = None
    if payload.calendar_entry_id is not None:
        calendar_entry = session.scalar(
            select(CalendarEntry)
            .where(
                CalendarEntry.id == payload.calendar_entry_id,
                CalendarEntry.organization_id == organization_id,
                CalendarEntry.business_id == business_id,
                CalendarEntry.archived_at.is_(None),
            )
            .with_for_update()
        )
        if calendar_entry is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Item do calendário não encontrado")
        if calendar_entry.content_item_id is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Este item do calendário já possui conteúdo",
            )
        if plan_id is not None and plan_id != calendar_entry.content_plan_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Plano incompatível")
        plan_id = calendar_entry.content_plan_id
        if calendar_entry.visual_preset_id is not None:
            if preset_id is not None and preset_id != calendar_entry.visual_preset_id:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Preset incompatível")
            preset_id = calendar_entry.visual_preset_id

    plan: ContentPlan | None = None
    if plan_id is not None:
        plan = session.scalar(
            select(ContentPlan).where(
                ContentPlan.id == plan_id,
                ContentPlan.organization_id == organization_id,
                ContentPlan.business_id == business_id,
                ContentPlan.archived_at.is_(None),
            )
        )
        if plan is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Plano de conteúdo não encontrado")
        if strategy_id is not None and strategy_id != plan.content_strategy_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Estratégia incompatível")
        if strategy_version_id is not None and strategy_version_id != plan.strategy_version_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Versão da estratégia incompatível",
            )
        strategy_id = plan.content_strategy_id
        strategy_version_id = plan.strategy_version_id

    strategy_version: StrategyVersion | None = None
    if strategy_version_id is not None:
        strategy_version = session.scalar(
            select(StrategyVersion).where(
                StrategyVersion.id == strategy_version_id,
                StrategyVersion.organization_id == organization_id,
                StrategyVersion.business_id == business_id,
            )
        )
        if strategy_version is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Versão da estratégia não encontrada")
        if strategy_id is not None and strategy_id != strategy_version.content_strategy_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Estratégia incompatível")
        strategy_id = strategy_version.content_strategy_id

    strategy: ContentStrategy | None = None
    if strategy_id is not None:
        strategy = session.scalar(
            select(ContentStrategy).where(
                ContentStrategy.id == strategy_id,
                ContentStrategy.organization_id == organization_id,
                ContentStrategy.business_id == business_id,
                ContentStrategy.archived_at.is_(None),
            )
        )
        if strategy is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Estratégia não encontrada")
        if strategy_version is None:
            selected_version_id = strategy.approved_version_id or strategy.current_version_id
            if selected_version_id is None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Estratégia sem versão disponível",
                )
            strategy_version = session.scalar(
                select(StrategyVersion).where(
                    StrategyVersion.id == selected_version_id,
                    StrategyVersion.organization_id == organization_id,
                    StrategyVersion.business_id == business_id,
                    StrategyVersion.content_strategy_id == strategy.id,
                )
            )
            if strategy_version is None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Versão da estratégia indisponível",
                )

    preset: VisualPreset | None = None
    if preset_id is not None:
        preset = session.scalar(
            select(VisualPreset).where(
                VisualPreset.id == preset_id,
                VisualPreset.organization_id == organization_id,
                VisualPreset.business_id == business_id,
                VisualPreset.is_active.is_(True),
            )
        )
        if preset is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Preset visual não encontrado")
        if brand is None or preset.brand_profile_id != brand.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Preset visual inconsistente")

    service: Service | None = None
    if payload.service_id is not None:
        service = session.scalar(
            select(Service).where(
                Service.id == payload.service_id,
                Service.organization_id == organization_id,
                Service.business_id == business_id,
                Service.is_active.is_(True),
            )
        )
        if service is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Serviço não encontrado")

    audience: AudienceSegment | None = None
    if payload.audience_segment_id is not None:
        audience = session.scalar(
            select(AudienceSegment).where(
                AudienceSegment.id == payload.audience_segment_id,
                AudienceSegment.organization_id == organization_id,
                AudienceSegment.business_id == business_id,
                AudienceSegment.is_active.is_(True),
            )
        )
        if audience is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Público não encontrado")

    marketing_objective: MarketingObjective | None = None
    if payload.marketing_objective_id is not None:
        marketing_objective = session.scalar(
            select(MarketingObjective).where(
                MarketingObjective.id == payload.marketing_objective_id,
                MarketingObjective.organization_id == organization_id,
                MarketingObjective.business_id == business_id,
                MarketingObjective.is_active.is_(True),
            )
        )
        if marketing_objective is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Objetivo não encontrado")

    media_asset: MediaAsset | None = None
    if payload.media_asset_id is not None:
        media_asset = session.scalar(
            select(MediaAsset).where(
                MediaAsset.id == payload.media_asset_id,
                MediaAsset.organization_id == organization_id,
                MediaAsset.business_id == business_id,
                MediaAsset.processing_status == "READY",
                MediaAsset.archived_at.is_(None),
            )
        )
        if media_asset is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mídia não encontrada")

    return GenerationLinks(
        strategy=strategy,
        strategy_version=strategy_version,
        plan=plan,
        calendar_entry=calendar_entry,
        preset=preset,
        service=service,
        audience=audience,
        marketing_objective=marketing_objective,
        media_asset=media_asset,
    )
