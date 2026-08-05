from __future__ import annotations

import json
from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.config import Settings
from growthos.dependencies import AuthContext, get_scoped_business
from growthos.models import (
    AIGeneration,
    AIGenerationAlternative,
    AIGenerationAttempt,
    AIGenerationFeedback,
    AIUsageDaily,
    AudienceSegment,
    BrandProfile,
    ContentStrategy,
    MarketingObjective,
    Service,
    StrategyVersion,
)
from growthos.models.base import utcnow
from growthos.schemas_ai import AIFeedbackCreate, AIGenerationCreate, AIGenerationRead
from growthos.services.ai_providers import (
    AIProvider,
    AIProviderError,
    MockGrowthProvider,
    OpenAICompatibleProvider,
    ProviderRequest,
)
from growthos.services.audit import add_audit_log
from growthos.services.sensitivity import VeterinarySensitivityClassifier, content_document


def _context(session: Session, organization_id: UUID, business_id: UUID) -> dict[str, object]:
    brand = session.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == organization_id, BrandProfile.business_id == business_id
        )
    )
    services = session.scalars(
        select(Service).where(
            Service.organization_id == organization_id,
            Service.business_id == business_id,
            Service.is_active.is_(True),
        )
    ).all()
    audiences = session.scalars(
        select(AudienceSegment).where(
            AudienceSegment.organization_id == organization_id,
            AudienceSegment.business_id == business_id,
            AudienceSegment.is_active.is_(True),
        )
    ).all()
    objectives = session.scalars(
        select(MarketingObjective).where(
            MarketingObjective.organization_id == organization_id,
            MarketingObjective.business_id == business_id,
            MarketingObjective.is_active.is_(True),
        )
    ).all()
    approved_strategies = session.execute(
        select(
            ContentStrategy.name,
            StrategyVersion.objective,
            StrategyVersion.positioning,
            StrategyVersion.funnel,
            StrategyVersion.channels,
            StrategyVersion.pillars,
        )
        .join(StrategyVersion, ContentStrategy.approved_version_id == StrategyVersion.id)
        .where(
            ContentStrategy.organization_id == organization_id,
            ContentStrategy.business_id == business_id,
            ContentStrategy.status == "APPROVED",
        )
        .order_by(ContentStrategy.starts_on.desc())
        .limit(3)
    ).all()
    return {
        "brand": {
            "name": brand.brand_name if brand else "",
            "description": brand.description if brand else "",
            "audience": brand.audience if brand else "",
            "tone": brand.tone_of_voice if brand else "",
            "preferred_words": brand.preferred_words if brand else [],
            "forbidden_words": brand.forbidden_words if brand else [],
            "calls_to_action": brand.calls_to_action if brand else [],
            "legal_rules": brand.legal_rules if brand else [],
            "image_restrictions": brand.image_restrictions if brand else [],
        },
        "services": [
            {"name": row.name, "description": row.description, "warnings": row.warnings}
            for row in services
        ],
        "audiences": [
            {"name": row.name, "needs": row.needs, "objections": row.objections}
            for row in audiences
        ],
        "objectives": [{"name": row.name, "description": row.description} for row in objectives],
        "planning": [
            {
                "name": name,
                "objective": objective,
                "positioning": positioning,
                "funnel": funnel,
                "channels": channels,
                "pillars": pillars,
            }
            for name, objective, positioning, funnel, channels, pillars in approved_strategies
        ],
    }


def _providers(settings: Settings) -> list[AIProvider]:
    result: list[AIProvider] = []
    if settings.ai_external_enabled and settings.openrouter_api_key:
        result.append(
            OpenAICompatibleProvider(
                name="openrouter",
                base_url=settings.openrouter_base_url,
                model=settings.openrouter_model,
                timeout=settings.openrouter_timeout_seconds,
                attempts=settings.openrouter_max_attempts,
                api_key=settings.openrouter_api_key,
            )
        )
    if settings.hermes_base_url:
        result.append(
            OpenAICompatibleProvider(
                name="hermes_ollama",
                base_url=settings.hermes_base_url,
                model=settings.hermes_model,
                timeout=settings.hermes_timeout_seconds,
                attempts=settings.hermes_max_attempts,
                native_ollama=True,
            )
        )
    result.append(MockGrowthProvider())
    return result


def _serialize(session: Session, row: AIGeneration) -> AIGenerationRead:
    alternatives = session.scalars(
        select(AIGenerationAlternative)
        .where(
            AIGenerationAlternative.generation_id == row.id,
            AIGenerationAlternative.organization_id == row.organization_id,
        )
        .order_by(AIGenerationAlternative.position)
    ).all()
    failed_attempts = session.scalars(
        select(AIGenerationAttempt).where(
            AIGenerationAttempt.generation_id == row.id,
            AIGenerationAttempt.organization_id == row.organization_id,
            AIGenerationAttempt.status == "FAILED",
        )
    ).all()
    fallback_message = None
    if failed_attempts:
        providers = ", ".join(attempt.provider for attempt in failed_attempts)
        fallback_message = f"{providers} indisponível; fallback seguro utilizado."
    return AIGenerationRead.model_validate(
        {
            **row.__dict__,
            "alternatives": alternatives,
            "simulated": row.provider == "mock",
            "fallback_message": fallback_message,
        }
    )


def generate(
    session: Session,
    context: AuthContext,
    business_id: UUID,
    payload: AIGenerationCreate,
    settings: Settings,
    parent_id: UUID | None = None,
) -> AIGenerationRead:
    business = get_scoped_business(session, context, business_id)
    today = date.today()
    usage = session.scalar(
        select(AIUsageDaily)
        .where(
            AIUsageDaily.organization_id == context.organization.id,
            AIUsageDaily.usage_date == today,
        )
        .with_for_update()
    )
    if usage and usage.generation_count >= settings.ai_daily_generation_limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Limite diário de gerações atingido")
    snapshot = _context(session, context.organization.id, business.id)
    prompt = json.dumps(
        {
            "task": payload.task,
            "instruction": payload.instruction,
            "source_text": payload.source_text,
            "context": snapshot,
            "alternatives": payload.alternatives,
        },
        ensure_ascii=False,
    )
    estimated_input = max(1, len(prompt) // 4)
    if estimated_input > settings.ai_max_input_tokens:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Contexto excede o limite de tokens"
        )
    generation = AIGeneration(
        organization_id=context.organization.id,
        business_id=business.id,
        requested_by_user_id=context.user.id,
        parent_generation_id=parent_id,
        task=payload.task.value,
        status="PROCESSING",
        instruction=payload.instruction,
        alternative_count=payload.alternatives,
        context_snapshot=snapshot,
        provider="pending",
        model="pending",
    )
    session.add(generation)
    session.flush()
    request = ProviderRequest(
        system=(
            "Você é o Growth Agent. Retorne somente JSON válido com a chave alternatives. "
            "Cada alternativa deve conter title, caption, cta, script, visual_prompt, "
            "strategy, sensitive e sensitivity_reason. Nunca publique, aprove ou "
            "prescreva orientação veterinária."
        ),
        prompt=prompt,
        alternatives=payload.alternatives,
        max_tokens=settings.ai_max_output_tokens,
    )
    chosen = None
    errors: list[str] = []
    for position, provider in enumerate(_providers(settings)):
        started = datetime.now(UTC)
        try:
            chosen = provider.generate(request)
            session.add(
                AIGenerationAttempt(
                    organization_id=context.organization.id,
                    generation_id=generation.id,
                    provider=chosen.provider,
                    model=chosen.model,
                    status="SUCCESS",
                    duration_ms=chosen.duration_ms,
                    created_at=started,
                )
            )
            generation.used_fallback = position > 0
            break
        except AIProviderError as exc:
            errors.append(f"{provider.name}:{exc.code}")
            session.add(
                AIGenerationAttempt(
                    organization_id=context.organization.id,
                    generation_id=generation.id,
                    provider=provider.name,
                    model=getattr(provider, "model", "unknown"),
                    status="FAILED",
                    duration_ms=max(1, int((datetime.now(UTC) - started).total_seconds() * 1000)),
                    error_code=exc.code,
                    created_at=started,
                )
            )
    if chosen is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Nenhum provider de IA disponível")
    classifier = VeterinarySensitivityClassifier()
    for index, item in enumerate(chosen.alternatives, 1):
        assessment = classifier.assess(
            content_document(
                title=str(item.get("title", "")),
                caption=str(item.get("caption", "")),
                objective=str(item.get("strategy", "")),
                audience="",
                cta=str(item.get("cta", "")),
                notes="",
                script=str(item.get("script", "")),
                visual_prompt=str(item.get("visual_prompt", "")),
                negative_prompt="",
            )
        )
        explicit_sensitive = bool(item.get("sensitive"))
        session.add(
            AIGenerationAlternative(
                organization_id=context.organization.id,
                business_id=business.id,
                generation_id=generation.id,
                position=index,
                payload=item,
                is_sensitive=assessment.is_sensitive or explicit_sensitive,
                sensitivity_codes=list(assessment.codes)
                + (["PROVIDER_SENSITIVE"] if explicit_sensitive else []),
                created_at=utcnow(),
            )
        )
    generation.status = "COMPLETED"
    generation.provider = chosen.provider
    generation.model = chosen.model
    generation.duration_ms = chosen.duration_ms
    generation.input_tokens = chosen.input_tokens or estimated_input
    generation.output_tokens = chosen.output_tokens
    generation.estimated_cost_usd = chosen.estimated_cost_usd
    if usage is None:
        usage = AIUsageDaily(
            organization_id=context.organization.id,
            usage_date=today,
            generation_count=0,
            input_tokens=0,
            output_tokens=0,
            updated_at=utcnow(),
        )
        session.add(usage)
    usage.generation_count += 1
    usage.input_tokens += generation.input_tokens
    usage.output_tokens += generation.output_tokens
    usage.updated_at = utcnow()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="ai.generation_completed",
        resource_type="ai_generation",
        resource_id=generation.id,
        details={
            "task": payload.task.value,
            "provider": chosen.provider,
            "model": chosen.model,
            "fallback": generation.used_fallback,
            "attempt_errors": errors,
        },
    )
    session.commit()
    session.refresh(generation)
    return _serialize(session, generation)


def list_generations(
    session: Session, context: AuthContext, business_id: UUID
) -> list[AIGenerationRead]:
    get_scoped_business(session, context, business_id)
    rows = session.scalars(
        select(AIGeneration)
        .where(
            AIGeneration.organization_id == context.organization.id,
            AIGeneration.business_id == business_id,
        )
        .order_by(AIGeneration.created_at.desc())
        .limit(50)
    ).all()
    return [_serialize(session, row) for row in rows]


def get_generation(session: Session, context: AuthContext, generation_id: UUID) -> AIGenerationRead:
    row = session.scalar(
        select(AIGeneration).where(
            AIGeneration.id == generation_id,
            AIGeneration.organization_id == context.organization.id,
        )
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Geração não encontrada")
    get_scoped_business(session, context, row.business_id)
    return _serialize(session, row)


def save_feedback(
    session: Session, context: AuthContext, generation_id: UUID, payload: AIFeedbackCreate
) -> None:
    row = get_generation(session, context, generation_id)
    existing = session.scalar(
        select(AIGenerationFeedback).where(
            AIGenerationFeedback.generation_id == generation_id,
            AIGenerationFeedback.user_id == context.user.id,
        )
    )
    if existing:
        existing.rating, existing.comment = payload.rating, payload.comment.strip()
    else:
        session.add(
            AIGenerationFeedback(
                organization_id=context.organization.id,
                generation_id=row.id,
                user_id=context.user.id,
                rating=payload.rating,
                comment=payload.comment.strip(),
                created_at=utcnow(),
            )
        )
    session.commit()
