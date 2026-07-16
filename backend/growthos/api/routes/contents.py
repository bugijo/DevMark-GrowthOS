from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
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
from growthos.domain.content import InvalidContentTransition, validate_transition
from growthos.domain.enums import (
    ApprovalComponent,
    ApprovalStage,
    ApprovalStatus,
    ContentStatus,
    JobStatus,
    Role,
)
from growthos.domain.permissions import Capability
from growthos.models import (
    Approval,
    AudienceSegment,
    BrandProfile,
    Business,
    CalendarEntry,
    ContentItem,
    ContentPlan,
    ContentStrategy,
    ContentVersion,
    ContentVersionMedia,
    Job,
    MarketingObjective,
    MediaAsset,
    Membership,
    Notification,
    Service,
    StrategyVersion,
    User,
    VisualPreset,
)
from growthos.models.base import utcnow
from growthos.schemas import (
    ApprovalRead,
    ChangesRequest,
    ContentGenerateRequest,
    ContentRead,
    ContentRevisionCreate,
    ContentVersionRead,
    ContentVisualRevisionCreate,
    DecisionRequest,
    ManualPublicationCreate,
)
from growthos.services.audit import add_audit_log
from growthos.services.providers import MockTextProvider, TextGenerationRequest
from growthos.services.visual_prompts import MockVisualPromptProvider, VisualPromptRequest

router = APIRouter()

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


def _is_business_portal_context(context: AuthContext) -> bool:
    return context.membership.role in _BUSINESS_PORTAL_ROLES


def _get_content(
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
    if _is_business_portal_context(context):
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
        published_by_user_id=content.published_by_user_id,
        change_request_comment=change_request_comment,
        current_version=ContentVersionRead.model_validate(version).model_copy(
            update={"media_asset_ids": media_asset_ids}
        ),
        approvals=[ApprovalRead.model_validate(approval) for approval in approvals],
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


def _email_job(
    session: Session,
    *,
    organization_id: UUID,
    user: User,
    subject: str,
    text: str,
    key: str,
) -> None:
    session.add(
        Job(
            organization_id=organization_id,
            type="notification.email.smtp",
            status=JobStatus.PENDING,
            payload={"to": user.email, "subject": subject, "text": text},
            idempotency_key=key,
        )
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
    for user, membership in recipients:
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
        _email_job(
            session,
            organization_id=content.organization_id,
            user=user,
            subject=title,
            text="Entre no GrowthOS para consultar a decisão do cliente.",
            key=f"{email_key}:{membership.id}",
        )


@dataclass(frozen=True)
class _GenerationLinks:
    strategy: ContentStrategy | None
    strategy_version: StrategyVersion | None
    plan: ContentPlan | None
    calendar_entry: CalendarEntry | None
    preset: VisualPreset | None
    service: Service | None
    audience: AudienceSegment | None
    marketing_objective: MarketingObjective | None
    media_asset: MediaAsset | None


def _resolve_generation_links(
    session: Session,
    context: AuthContext,
    payload: ContentGenerateRequest,
    brand: BrandProfile | None,
) -> _GenerationLinks:
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

    return _GenerationLinks(
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


def _brand_snapshot(brand: BrandProfile | None) -> dict[str, object]:
    if brand is None:
        return {}
    return {
        "id": str(brand.id),
        "brand_name": brand.brand_name,
        "public_name": brand.public_name,
        "segment": brand.segment,
        "audience": brand.audience,
        "primary_colors": list(brand.primary_colors),
        "tone_of_voice": brand.tone_of_voice,
        "preferred_words": list(brand.preferred_words),
        "forbidden_words": list(brand.forbidden_words),
        "calls_to_action": list(brand.calls_to_action),
    }


def _preset_snapshot(preset: VisualPreset | None) -> dict[str, object]:
    if preset is None:
        return {}
    return {
        "id": str(preset.id),
        "version": preset.version,
        "name": preset.name,
        "objective": preset.objective,
        "format": preset.format,
        "aspect_ratio": preset.aspect_ratio,
        "creation_mode": preset.creation_mode,
        "color_palette": list(preset.color_palette),
        "fonts": list(preset.fonts),
        "logo_media_asset_id": (
            str(preset.logo_media_asset_id) if preset.logo_media_asset_id else None
        ),
        "logo_position": preset.logo_position,
        "logo_scale_percent": preset.logo_scale_percent,
        "safe_margins": dict(preset.safe_margins),
        "background_style": preset.background_style,
        "photographic_style": preset.photographic_style,
        "realism_level": preset.realism_level,
        "lighting": preset.lighting,
        "composition": preset.composition,
        "max_text_characters": preset.max_text_characters,
        "text_rules": list(preset.text_rules),
        "base_prompt": preset.base_prompt,
        "negative_prompt": preset.negative_prompt,
        "allowed_elements": list(preset.allowed_elements),
        "forbidden_elements": list(preset.forbidden_elements),
        "visual_signature": preset.visual_signature,
        "default_cta": preset.default_cta,
    }


def _scoped_visual_preset(
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


def _scoped_ready_image(
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


@router.post("/generate", response_model=ContentRead, status_code=status.HTTP_201_CREATED)
def generate_content(
    payload: ContentGenerateRequest,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_CREATE)
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
    links = _resolve_generation_links(session, context, payload, brand)
    audience_text = (
        (links.audience.description or links.audience.name)
        if links.audience is not None
        else (brand.audience if brand else "")
    )
    provider = MockTextProvider()
    result = provider.generate(
        TextGenerationRequest(
            brand_name=brand.brand_name if brand else business.name,
            objective=payload.objective,
            channel=payload.channel,
            format=payload.format,
            audience=audience_text,
            tone_of_voice=brand.tone_of_voice if brand else "",
            cta=(brand.calls_to_action[0] if brand and brand.calls_to_action else ""),
        )
    )
    visual_prompt = ""
    negative_prompt = ""
    preset_snapshot = _preset_snapshot(links.preset)
    if links.preset is not None and brand is not None:
        visual_result = MockVisualPromptProvider().generate(
            VisualPromptRequest(
                brand_name=brand.brand_name,
                objective=payload.objective,
                audience=audience_text,
                format=payload.format or links.preset.format,
                aspect_ratio=links.preset.aspect_ratio,
                creation_mode=links.preset.creation_mode,
                tone_of_voice=brand.tone_of_voice,
                base_prompt=links.preset.base_prompt,
                negative_prompt=links.preset.negative_prompt,
                background_style=links.preset.background_style,
                photographic_style=links.preset.photographic_style,
                lighting=links.preset.lighting,
                composition=links.preset.composition,
                realism_level=links.preset.realism_level,
                allowed_elements=tuple(links.preset.allowed_elements),
                forbidden_elements=tuple(links.preset.forbidden_elements),
            )
        )
        visual_prompt = visual_result.prompt
        negative_prompt = visual_result.negative_prompt
        preset_snapshot["prompt_provider"] = visual_result.provider_name
        preset_snapshot["prompt_provider_reference"] = visual_result.provider_reference
    content = ContentItem(
        organization_id=context.organization.id,
        business_id=business.id,
        status=ContentStatus.DRAFT,
        content_strategy_id=links.strategy.id if links.strategy else None,
        strategy_version_id=links.strategy_version.id if links.strategy_version else None,
        content_plan_id=links.plan.id if links.plan else None,
        calendar_entry_id=links.calendar_entry.id if links.calendar_entry else None,
        visual_preset_id=links.preset.id if links.preset else None,
        scheduled_for=(links.calendar_entry.suggested_for if links.calendar_entry else None),
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
        service_id=links.service.id if links.service else None,
        audience_segment_id=links.audience.id if links.audience else None,
        marketing_objective_id=(
            links.marketing_objective.id if links.marketing_objective else None
        ),
        notes=payload.notes.strip(),
        script=payload.script.strip(),
        visual_prompt=visual_prompt,
        negative_prompt=negative_prompt,
        brand_context_snapshot=_brand_snapshot(brand),
        visual_preset_snapshot=preset_snapshot,
        provider_name=result.provider_name,
        created_by_user_id=context.user.id,
    )
    session.add(version)
    session.flush()
    content.current_version_id = version.id
    if links.media_asset is not None:
        session.add(
            ContentVersionMedia(
                organization_id=context.organization.id,
                business_id=business.id,
                content_version_id=version.id,
                media_asset_id=links.media_asset.id,
                role="PRIMARY",
                sort_order=0,
                created_by_user_id=context.user.id,
            )
        )
    if links.calendar_entry is not None:
        links.calendar_entry.content_item_id = content.id
        links.calendar_entry.status = "GENERATED"
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="content.generated",
        resource_type="content_item",
        resource_id=content.id,
        details={
            "provider": result.provider_name,
            "visual_provider": "mock" if links.preset else None,
            "version": 1,
            "strategy_id": str(links.strategy.id) if links.strategy else None,
            "content_plan_id": str(links.plan.id) if links.plan else None,
            "calendar_entry_id": (str(links.calendar_entry.id) if links.calendar_entry else None),
            "visual_preset_id": str(links.preset.id) if links.preset else None,
            "media_asset_id": str(links.media_asset.id) if links.media_asset else None,
        },
    )
    session.commit()
    return _serialize(session, content)


@router.get("", response_model=list[ContentRead])
def list_contents(
    business_id: UUID | None = Query(default=None),
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[ContentRead]:
    require_capability(context, Capability.CONTENT_VIEW)
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
    if _is_business_portal_context(context):
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
    return [_serialize(session, content) for content in contents]


@router.get("/{content_id}", response_model=ContentRead)
def get_content(
    content_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_VIEW)
    return _serialize(session, _get_content(session, context, content_id))


@router.post("/{content_id}/submit-internal", response_model=ContentRead)
def submit_internal(
    content_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_SUBMIT_INTERNAL)
    content = _get_content(session, context, content_id, for_update=True)
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
    require_capability(context, Capability.CONTENT_SEND_CLIENT)
    content = _get_content(session, context, content_id, for_update=True)
    version = _get_current_version(session, content)
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
    previous = _transition(content, ContentStatus.CLIENT_REVIEW)
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
    for user, reviewer in reviewers:
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
        _email_job(
            session,
            organization_id=context.organization.id,
            user=user,
            subject="Novo conteúdo para revisar",
            text="Entre no GrowthOS para revisar o texto e a imagem do conteúdo.",
            key=f"content-review:{content.id}:{version.id}:{reviewer.id}",
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
    return _serialize(session, content)


@router.post("/{content_id}/approve", response_model=ContentRead)
def approve_content(
    content_id: UUID,
    payload: DecisionRequest | None = None,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_DECIDE_CLIENT)
    content = _get_content(session, context, content_id, for_update=True)
    if context.membership.business_id != content.business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Aprovação fora do cliente permitido")
    version = _get_current_version(session, content)
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
    previous = _transition(content, ContentStatus.APPROVED)
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
    return _serialize(session, content)


@router.post(
    "/{content_id}/decisions/{component}/approve",
    response_model=ContentRead,
)
def approve_content_component(
    content_id: UUID,
    component: ApprovalComponent,
    payload: DecisionRequest | None = None,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_DECIDE_CLIENT)
    content = _get_content(session, context, content_id, for_update=True)
    if context.membership.business_id != content.business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Aprovação fora do cliente permitido")
    version = _get_current_version(session, content)
    approval = _pending_approval(session, content, version, component)
    approval.status = ApprovalStatus.APPROVED
    approval.decided_by_user_id = context.user.id
    approval.decision_comment = payload.comment if payload else None
    approval.decided_at = utcnow()
    session.flush()
    previous = content.status
    completed = _all_components_approved(session, content, version)
    if completed:
        previous = _transition(content, ContentStatus.APPROVED)
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
    return _serialize(session, content)


def _request_component_changes(
    session: Session,
    context: AuthContext,
    content: ContentItem,
    component: ApprovalComponent,
    comment: str,
) -> ContentRead:
    current = _get_current_version(session, content)
    approval = _pending_approval(session, content, current, component)
    previous = _transition(content, ContentStatus.CHANGES_REQUESTED)
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
            "comment": comment,
            "cancelled_components": [pending.component.value for pending in obsolete],
        },
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
    require_capability(context, Capability.CONTENT_DECIDE_CLIENT)
    content = _get_content(session, context, content_id, for_update=True)
    if context.membership.business_id != content.business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Revisão fora do cliente permitido")
    return _request_component_changes(
        session,
        context,
        content,
        ApprovalComponent.TEXT,
        payload.comment.strip(),
    )


@router.post(
    "/{content_id}/decisions/{component}/request-changes",
    response_model=ContentRead,
)
def request_content_component_changes(
    content_id: UUID,
    component: ApprovalComponent,
    payload: ChangesRequest,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_DECIDE_CLIENT)
    content = _get_content(session, context, content_id, for_update=True)
    if context.membership.business_id != content.business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Revisão fora do cliente permitido")
    return _request_component_changes(
        session,
        context,
        content,
        component,
        payload.comment.strip(),
    )


@router.post("/{content_id}/revisions", response_model=ContentRead)
def create_revision(
    content_id: UUID,
    payload: ContentRevisionCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_EDIT_TEXT)
    content = _get_content(session, context, content_id, for_update=True)
    current = _get_current_version(session, content)
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

    previous = _transition(content, ContentStatus.DRAFT)
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
    return _serialize(session, content)


@router.post("/{content_id}/visual-revisions", response_model=ContentRead)
def create_visual_revision(
    content_id: UUID,
    payload: ContentVisualRevisionCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_EDIT_VISUAL)
    content = _get_content(session, context, content_id, for_update=True)
    current = _get_current_version(session, content)
    fields = payload.model_fields_set

    old_preset_id = content.visual_preset_id
    new_preset_id = old_preset_id
    visual_prompt = current.visual_prompt
    negative_prompt = current.negative_prompt
    preset_snapshot = dict(current.visual_preset_snapshot)
    prompt_source = "carried"

    if "visual_preset_id" in fields:
        new_preset_id = payload.visual_preset_id
        if new_preset_id is None:
            preset_snapshot = {}
            visual_prompt = ""
            negative_prompt = ""
            prompt_source = "cleared"
        else:
            preset, brand = _scoped_visual_preset(session, content, new_preset_id)
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
            preset_snapshot = _preset_snapshot(preset)
            preset_snapshot["prompt_provider"] = result.provider_name
            preset_snapshot["prompt_provider_reference"] = result.provider_reference
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
        media_asset = _scoped_ready_image(session, content, payload.media_asset_id)
        next_media = [(media_asset.id, "PRIMARY", 0)]

    old_media = [
        (association.media_asset_id, association.role, association.sort_order)
        for association in previous_media
    ]
    if (
        new_preset_id == old_preset_id
        and visual_prompt == current.visual_prompt
        and negative_prompt == current.negative_prompt
        and preset_snapshot == current.visual_preset_snapshot
        and next_media == old_media
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Altere ao menos um elemento visual antes de criar uma nova versão",
        )

    previous_status = _transition(content, ContentStatus.DRAFT)
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
        visual_preset_snapshot=preset_snapshot,
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
    return _serialize(session, content)


@router.post("/{content_id}/publication", response_model=ContentRead)
def record_manual_publication(
    content_id: UUID,
    payload: ManualPublicationCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.PUBLICATION_RECORD)
    content = _get_content(session, context, content_id, for_update=True)
    idempotency_key = payload.idempotency_key.strip()
    channel = payload.channel.strip()
    if len(idempotency_key) < 8 or not channel:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Canal e chave de idempotência são obrigatórios",
        )
    if content.status == ContentStatus.PUBLISHED:
        if content.publication_idempotency_key == idempotency_key:
            return _serialize(session, content)
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
        _transition(content, ContentStatus.SCHEDULED)
    if content.scheduled_for is None:
        content.scheduled_for = payload.published_at
    _transition(content, ContentStatus.PUBLISHED)
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
            "version_id": str(_get_current_version(session, content).id),
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
    return _serialize(session, content)
