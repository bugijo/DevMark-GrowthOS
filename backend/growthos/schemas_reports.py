from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PeriodReportRead(BaseModel):
    organization_id: UUID
    business_id: UUID
    starts_on: date
    ends_on: date
    content_total: int = Field(ge=0)
    content_by_status: dict[str, int]
    content_versions_total: int = Field(ge=0)
    revisions_total: int = Field(ge=0)
    approvals_by_component: dict[str, dict[str, int]]
    manual_publications_total: int = Field(ge=0)
    publications_by_channel: dict[str, int]
    strategies_total: int = Field(ge=0)
    approved_strategies_total: int = Field(ge=0)
    calendar_entries_total: int = Field(ge=0)
    unavailable_metrics: list[str]
    ai_confirmed_cost_usd: Decimal = Decimal("0")
    ai_estimated_cost_usd: Decimal = Decimal("0")
    ai_unknown_cost_count: int = Field(default=0, ge=0)
