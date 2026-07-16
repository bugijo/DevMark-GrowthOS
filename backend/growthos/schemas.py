from datetime import datetime
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from growthos.domain.enums import (
    ApprovalComponent,
    ApprovalStage,
    ApprovalStatus,
    ContentStatus,
    Role,
)

EmailValue = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=320,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailValue
    name: str


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    slug: str


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    role: Role
    business_id: UUID | None


class LoginRequest(BaseModel):
    email: EmailValue
    password: str = Field(min_length=8, max_length=256)


class AuthResponse(BaseModel):
    user: UserRead
    membership: MembershipRead
    organization: OrganizationRead
    csrf_token: str


class BusinessCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    segment: str = Field(default="", max_length=120)


class BusinessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    segment: str | None = Field(default=None, max_length=120)


class BusinessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    name: str
    segment: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ReviewerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailValue
    password: str = Field(min_length=8, max_length=256)


class ReviewerRead(BaseModel):
    user: UserRead
    membership: MembershipRead


class BrandProfileUpsert(BaseModel):
    brand_name: str = Field(min_length=1, max_length=200)
    public_name: str = Field(default="", max_length=200)
    description: str = ""
    segment: str = Field(default="", max_length=120)
    audience: str = ""
    primary_colors: list[str] = Field(default_factory=list)
    tone_of_voice: str = ""
    preferred_words: list[str] = Field(default_factory=list)
    forbidden_words: list[str] = Field(default_factory=list)
    slogan: str = Field(default="", max_length=300)
    differentiators: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    contacts: dict[str, Any] | str | None = None
    links: list[str] = Field(default_factory=list)
    calls_to_action: list[str] = Field(default_factory=list)
    internal_notes: str = ""


class BrandProfileRead(BrandProfileUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    business_id: UUID
    created_at: datetime
    updated_at: datetime


class ContentGenerateRequest(BaseModel):
    business_id: UUID
    objective: str = Field(min_length=2, max_length=1000)
    channel: str = Field(default="INSTAGRAM", min_length=2, max_length=80)
    format: str = Field(default="FEED", min_length=2, max_length=80)
    content_strategy_id: UUID | None = None
    strategy_version_id: UUID | None = None
    content_plan_id: UUID | None = None
    calendar_entry_id: UUID | None = None
    visual_preset_id: UUID | None = None
    service_id: UUID | None = None
    audience_segment_id: UUID | None = None
    marketing_objective_id: UUID | None = None
    media_asset_id: UUID | None = None
    notes: str = Field(default="", max_length=10_000)
    script: str = Field(default="", max_length=30_000)


class ContentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    version_number: int
    title: str
    caption: str
    channel: str
    format: str
    objective: str
    audience: str
    cta: str
    service_id: UUID | None
    audience_segment_id: UUID | None
    marketing_objective_id: UUID | None
    notes: str
    script: str
    visual_prompt: str
    negative_prompt: str
    brand_context_snapshot: dict[str, Any]
    visual_preset_snapshot: dict[str, Any]
    media_asset_ids: list[UUID] = Field(default_factory=list)
    provider_name: str
    created_at: datetime


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    content_item_id: UUID
    content_version_id: UUID
    stage: ApprovalStage
    component: ApprovalComponent
    status: ApprovalStatus
    requested_by_user_id: UUID | None
    decided_by_user_id: UUID | None
    decision_comment: str | None
    decided_at: datetime | None


class ContentRead(BaseModel):
    id: UUID
    organization_id: UUID
    business_id: UUID
    status: ContentStatus
    content_strategy_id: UUID | None = None
    strategy_version_id: UUID | None = None
    content_plan_id: UUID | None = None
    calendar_entry_id: UUID | None = None
    visual_preset_id: UUID | None = None
    scheduled_for: datetime | None = None
    published_at: datetime | None = None
    publication_channel: str | None = None
    publication_reference: str | None = None
    published_by_user_id: UUID | None = None
    change_request_comment: str | None = None
    current_version: ContentVersionRead
    approvals: list[ApprovalRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DecisionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class ChangesRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=2000)


class ContentRevisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    caption: str = Field(min_length=1, max_length=10_000)
    cta: str = Field(default="", max_length=300)
    notes: str | None = Field(default=None, max_length=10_000)
    script: str | None = Field(default=None, max_length=30_000)


class ContentVisualRevisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visual_preset_id: UUID | None = None
    media_asset_id: UUID | None = None
    visual_prompt: str | None = Field(default=None, max_length=30_000)
    negative_prompt: str | None = Field(default=None, max_length=30_000)

    @model_validator(mode="after")
    def require_at_least_one_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("informe ao menos uma alteração visual")
        return self


class ManualPublicationCreate(BaseModel):
    channel: str = Field(min_length=2, max_length=80)
    published_at: datetime
    reference: str | None = Field(default=None, max_length=2048)
    idempotency_key: str = Field(min_length=8, max_length=200)

    @field_validator("published_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("published_at deve informar o fuso horário")
        return value


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    business_id: UUID | None
    type: str
    title: str
    message: str
    resource_type: str | None
    resource_id: UUID | None
    read_at: datetime | None
    created_at: datetime


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    business_id: UUID | None
    actor_user_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID | None
    details: dict[str, Any]
    created_at: datetime


class HealthRead(BaseModel):
    status: str
    database: str
    provider: str
