from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ComparisonActorRead(BaseModel):
    name: str


class VersionDecisionRead(BaseModel):
    status: str
    component: str | None = None
    comment: str | None = None
    decided_at: datetime | None = None
    decided_by: ComparisonActorRead | None = None


class VersionSummaryRead(BaseModel):
    id: UUID
    version_number: int
    created_at: datetime
    author: ComparisonActorRead
    is_current: bool
    is_approved: bool
    decisions: list[VersionDecisionRead] = Field(default_factory=list)


class ContentTextFieldsRead(BaseModel):
    title: str
    caption: str
    objective: str
    audience: str
    cta: str
    script: str


class ContentVisualFieldsRead(BaseModel):
    channel: str
    format: str
    preset: dict[str, Any] = Field(default_factory=dict)
    media_asset_ids: list[UUID] = Field(default_factory=list)


class ContentVersionComparisonSideRead(VersionSummaryRead):
    text: ContentTextFieldsRead
    visual: ContentVisualFieldsRead


class ContentVersionHistoryRead(BaseModel):
    content_id: UUID
    business_id: UUID
    current_version_id: UUID
    versions: list[VersionSummaryRead]


class ContentVersionComparisonRead(BaseModel):
    content_id: UUID
    business_id: UUID
    base: ContentVersionComparisonSideRead
    target: ContentVersionComparisonSideRead
    changed_fields: list[str]


class StrategyFieldsRead(BaseModel):
    objective: str
    positioning: str
    funnel: list[str]
    channels: list[str]
    pillars: list[str | dict[str, Any]]
    planned_indicators: list[str]
    services: list[dict[str, Any]] = Field(default_factory=list)
    audiences: list[dict[str, Any]] = Field(default_factory=list)
    marketing_objectives: list[dict[str, Any]] = Field(default_factory=list)


class StrategyVersionComparisonSideRead(VersionSummaryRead):
    strategy: StrategyFieldsRead


class StrategyVersionHistoryRead(BaseModel):
    strategy_id: UUID
    business_id: UUID
    current_version_id: UUID
    approved_version_id: UUID | None
    versions: list[VersionSummaryRead]


class StrategyVersionComparisonRead(BaseModel):
    strategy_id: UUID
    business_id: UUID
    base: StrategyVersionComparisonSideRead
    target: StrategyVersionComparisonSideRead
    changed_fields: list[str]
