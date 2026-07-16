from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext, get_scoped_business
from growthos.domain.enums import ContentStatus
from growthos.models import BrandProfile, ContentItem, ContentVersion, ContentVersionMedia
from growthos.schemas import ContentGenerateRequest, ContentRead
from growthos.services.audit import add_audit_log
from growthos.services.content.generation_context import resolve_generation_links
from growthos.services.content.read_models import serialize_content
from growthos.services.content.snapshots import brand_snapshot, preset_snapshot
from growthos.services.providers import MockTextProvider, TextGenerationRequest
from growthos.services.visual_prompts import MockVisualPromptProvider, VisualPromptRequest


def generate_content(
    session: Session,
    context: AuthContext,
    payload: ContentGenerateRequest,
) -> ContentRead:
    business = get_scoped_business(session, context, payload.business_id)
    brand = session.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == context.organization.id,
            BrandProfile.business_id == business.id,
        )
    )
    links = resolve_generation_links(session, context, payload, brand)
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
    visual_preset_snapshot = preset_snapshot(links.preset)
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
        visual_preset_snapshot["prompt_provider"] = visual_result.provider_name
        visual_preset_snapshot["prompt_provider_reference"] = visual_result.provider_reference
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
        brand_context_snapshot=brand_snapshot(brand),
        visual_preset_snapshot=visual_preset_snapshot,
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
    return serialize_content(session, content, context)
