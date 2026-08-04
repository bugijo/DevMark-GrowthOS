from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AITask(StrEnum):
    AUDIT = "AUDIT"
    MONTHLY_STRATEGY = "MONTHLY_STRATEGY"
    EDITORIAL_CALENDAR = "EDITORIAL_CALENDAR"
    CONTENT_IDEAS = "CONTENT_IDEAS"
    CAPTION = "CAPTION"
    TITLE = "TITLE"
    CTA = "CTA"
    SCRIPT = "SCRIPT"
    VISUAL_PROMPT = "VISUAL_PROMPT"
    CONTENT_REPURPOSE = "CONTENT_REPURPOSE"
    TONE_REVIEW = "TONE_REVIEW"
    SENSITIVITY_CLASSIFICATION = "SENSITIVITY_CLASSIFICATION"


class AIGenerationCreate(BaseModel):
    task: AITask
    instruction: str = Field(default="", max_length=2000)
    alternatives: Literal[1, 3] = 1
    source_text: str = Field(default="", max_length=12_000)

    @field_validator("instruction", "source_text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class AIAlternativeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    position: int
    payload: dict[str, Any]
    is_sensitive: bool
    sensitivity_codes: list[str]
    created_at: datetime


class AIGenerationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    business_id: UUID
    parent_generation_id: UUID | None
    task: str
    status: str
    instruction: str
    alternative_count: int
    provider: str
    model: str
    used_fallback: bool
    duration_ms: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float | None
    error_code: str | None
    created_at: datetime
    alternatives: list[AIAlternativeRead]
    simulated: bool
    requires_approval: bool = True
    can_publish_automatically: bool = False


class AIFeedbackCreate(BaseModel):
    rating: Literal["HELPFUL", "NOT_HELPFUL"]
    comment: str = Field(default="", max_length=2000)


class AIUsageRead(BaseModel):
    usage_date: date
    generation_count: int
    daily_limit: int
    input_tokens: int
    output_tokens: int


class AIStatusRead(BaseModel):
    external_enabled: bool
    order: list[str]
    openrouter_configured: bool
    hermes_configured: bool
    mock_available: bool = True
    daily_limit: int
    max_input_tokens: int
    max_output_tokens: int
