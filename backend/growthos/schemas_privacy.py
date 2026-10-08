from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConsentCreate(BaseModel):
    purpose_code: str = Field(min_length=2, max_length=80)
    policy_version: str = Field(min_length=1, max_length=40)
    accepted: bool


class ConsentRead(ConsentCreate):
    id: UUID
    source: str
    created_at: datetime


class DataPurposeRead(BaseModel):
    id: UUID
    code: str
    name: str
    purpose: str
    legal_basis: str
    data_categories: str
    retention_days: int
    is_active: bool


class RetentionPolicyUpdate(BaseModel):
    retention_days: int = Field(ge=1, le=36500)
    legal_hold: bool = False
    justification: str = Field(min_length=5, max_length=2000)


class RetentionPolicyRead(RetentionPolicyUpdate):
    id: UUID
    resource_type: str
    updated_at: datetime


class PrivacyRequestCreate(BaseModel):
    request_type: str = Field(pattern="^(EXPORT|DELETION)$")
    reason: str = Field(min_length=3, max_length=2000)


class PrivacyResolution(BaseModel):
    decision: str = Field(pattern="^(COMPLETE|REJECT)$")
    notes: str = Field(min_length=5, max_length=4000)


class PrivacyRequestRead(BaseModel):
    id: UUID
    request_type: str
    status: str
    reason: str
    subject_user_id: UUID
    resolution_notes: str | None
    processed_at: datetime | None
    created_at: datetime


class PrivacyExportRead(BaseModel):
    format_version: str = "1.1"
    generated_at: datetime
    organization: dict[str, str]
    subject: dict[str, str]
    memberships: list[dict[str, str | None]]
    consents: list[ConsentRead]
    requests: list[PrivacyRequestRead]
    ai_generations: list[dict[str, Any]] = Field(default_factory=list)


class RetentionRunCreate(BaseModel):
    resource_type: str = Field(
        pattern="^(ai_generations|ai_generation_attempts|ai_generation_alternatives|"
        "ai_generation_feedback|ai_generation_snapshots|ai_usage_daily|ai_generation_errors|"
        "sales_leads)$"
    )
    dry_run: bool = True


class RetentionRunRead(BaseModel):
    resource_type: str
    dry_run: bool
    cutoff_at: datetime
    affected_count: int
    audit_log_id: UUID | None = None
