from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlanningInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StrategyVersionInput(PlanningInput):
    objective: str = Field(min_length=2, max_length=2000)
    positioning: str = Field(default="", max_length=4000)
    funnel: list[str] = Field(default_factory=list, max_length=20)
    channels: list[str] = Field(default_factory=list, max_length=20)
    pillars: list[str] = Field(default_factory=list, max_length=30)
    planned_indicators: list[str] = Field(default_factory=list, max_length=30)
    service_ids: list[UUID] = Field(default_factory=list, max_length=50)
    audience_ids: list[UUID] = Field(default_factory=list, max_length=50)
    marketing_objective_ids: list[UUID] = Field(default_factory=list, max_length=50)


class StrategyCreate(StrategyVersionInput):
    name: str = Field(min_length=2, max_length=240)
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.starts_on > self.ends_on:
            raise ValueError("starts_on deve ser anterior ou igual a ends_on")
        return self


class StrategyVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version_number: int
    objective: str
    positioning: str
    funnel: list[str]
    channels: list[str]
    pillars: list[str | dict[str, object]]
    planned_indicators: list[str]
    service_snapshots: list[dict[str, object]]
    audience_snapshots: list[dict[str, object]]
    objective_snapshots: list[dict[str, object]]
    source: str
    provider_name: str
    provider_reference: str
    created_at: datetime


class StrategyRead(BaseModel):
    id: UUID
    organization_id: UUID
    business_id: UUID
    name: str
    starts_on: date
    ends_on: date
    status: str
    current_version: StrategyVersionRead
    approved_version_id: UUID | None
    decision_comment: str | None
    submitted_at: datetime | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StrategyDecision(PlanningInput):
    decision: str = Field(pattern="^(APPROVE|CHANGES_REQUESTED)$")
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_change_comment(self) -> Self:
        if self.decision == "CHANGES_REQUESTED" and not self.comment:
            raise ValueError("comentário é obrigatório ao pedir alterações")
        return self


class ContentPlanCreate(PlanningInput):
    strategy_id: UUID
    name: str = Field(min_length=2, max_length=240)
    starts_on: date
    ends_on: date
    frequency: str = Field(default="SEMANAL", max_length=120)

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.starts_on > self.ends_on:
            raise ValueError("starts_on deve ser anterior ou igual a ends_on")
        return self


class ContentPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    business_id: UUID
    content_strategy_id: UUID
    strategy_version_id: UUID
    name: str
    starts_on: date
    ends_on: date
    frequency: str
    status: str
    created_at: datetime
    updated_at: datetime


class CalendarEntryCreate(PlanningInput):
    title: str = Field(min_length=2, max_length=300)
    objective: str = Field(min_length=2, max_length=2000)
    audience: str = Field(default="", max_length=2000)
    channel: str = Field(default="INSTAGRAM", min_length=2, max_length=80)
    format: str = Field(default="FEED", min_length=2, max_length=80)
    suggested_for: datetime
    visual_preset_id: UUID | None = None
    notes: str = Field(default="", max_length=4000)


class CalendarEntryUpdate(PlanningInput):
    title: str | None = Field(default=None, min_length=2, max_length=300)
    objective: str | None = Field(default=None, min_length=2, max_length=2000)
    audience: str | None = Field(default=None, max_length=2000)
    channel: str | None = Field(default=None, min_length=2, max_length=80)
    format: str | None = Field(default=None, min_length=2, max_length=80)
    suggested_for: datetime | None = None
    visual_preset_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("informe ao menos uma alteração")
        return self


class CalendarEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    business_id: UUID
    content_plan_id: UUID
    content_item_id: UUID | None
    visual_preset_id: UUID | None
    title: str
    objective: str
    audience: str
    channel: str
    format: str
    suggested_for: datetime
    status: str
    notes: str
    created_at: datetime
    updated_at: datetime
