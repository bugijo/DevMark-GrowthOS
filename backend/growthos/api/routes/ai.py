from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.config import Settings, get_settings
from growthos.database import get_session
from growthos.dependencies import AuthContext, get_current_context, require_capability, require_csrf
from growthos.domain.permissions import Capability
from growthos.models import AIGeneration, AIUsageDaily
from growthos.schemas_ai import (
    AIFeedbackCreate,
    AIGenerationCreate,
    AIGenerationRead,
    AIStatusRead,
    AITask,
    AIUsageRead,
)
from growthos.services import growth_agent

router = APIRouter()


@router.get("/ai/status", response_model=AIStatusRead)
def ai_status(
    context: AuthContext = Depends(get_current_context),
    settings: Settings = Depends(get_settings),
) -> AIStatusRead:
    require_capability(context, Capability.PROVIDER_CONFIG_VIEW)
    return AIStatusRead(
        external_enabled=settings.ai_external_enabled,
        order=["OPENROUTER", "HERMES_OLLAMA", "MOCK"],
        openrouter_configured=bool(settings.ai_external_enabled and settings.openrouter_api_key),
        hermes_configured=bool(settings.hermes_base_url),
        daily_limit=settings.ai_daily_generation_limit,
        max_input_tokens=settings.ai_max_input_tokens,
        max_output_tokens=settings.ai_max_output_tokens,
    )


@router.get("/ai/usage", response_model=AIUsageRead)
def ai_usage(
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AIUsageRead:
    require_capability(context, Capability.PROVIDER_CONFIG_VIEW)
    today = date.today()
    row = session.scalar(
        select(AIUsageDaily).where(
            AIUsageDaily.organization_id == context.organization.id,
            AIUsageDaily.usage_date == today,
        )
    )
    return AIUsageRead(
        usage_date=today,
        generation_count=row.generation_count if row else 0,
        daily_limit=settings.ai_daily_generation_limit,
        input_tokens=row.input_tokens if row else 0,
        output_tokens=row.output_tokens if row else 0,
    )


@router.post(
    "/businesses/{business_id}/ai/generations",
    response_model=AIGenerationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_generation(
    business_id: UUID,
    payload: AIGenerationCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AIGenerationRead:
    require_capability(context, Capability.CONTENT_CREATE)
    return growth_agent.generate(session, context, business_id, payload, settings)


@router.get("/businesses/{business_id}/ai/generations", response_model=list[AIGenerationRead])
def list_generations(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[AIGenerationRead]:
    require_capability(context, Capability.CONTENT_VIEW)
    return growth_agent.list_generations(session, context, business_id)


@router.get("/ai/generations/{generation_id}", response_model=AIGenerationRead)
def get_generation(
    generation_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> AIGenerationRead:
    require_capability(context, Capability.CONTENT_VIEW)
    return growth_agent.get_generation(session, context, generation_id)


@router.post(
    "/ai/generations/{generation_id}/regenerate",
    response_model=AIGenerationRead,
    status_code=status.HTTP_201_CREATED,
)
def regenerate(
    generation_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AIGenerationRead:
    require_capability(context, Capability.CONTENT_CREATE)
    previous = session.scalar(
        select(AIGeneration).where(
            AIGeneration.id == generation_id,
            AIGeneration.organization_id == context.organization.id,
        )
    )
    if previous is None:
        growth_agent.get_generation(session, context, generation_id)
        raise AssertionError("unreachable")
    growth_agent.get_generation(session, context, generation_id)
    payload = AIGenerationCreate(
        task=AITask(previous.task),
        instruction=previous.instruction,
        alternatives=3 if previous.alternative_count == 3 else 1,
    )
    return growth_agent.generate(
        session, context, previous.business_id, payload, settings, parent_id=previous.id
    )


@router.post("/ai/generations/{generation_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
def feedback(
    generation_id: UUID,
    payload: AIFeedbackCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> Response:
    require_capability(context, Capability.CONTENT_VIEW)
    growth_agent.save_feedback(session, context, generation_id, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
