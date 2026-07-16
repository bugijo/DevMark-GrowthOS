from datetime import datetime, time
from typing import Annotated, Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from growthos.schemas_catalog import VisualPresetCreate

ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=300),
]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10_000)]
RuleText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1000),
]
ColorValue = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=4,
        max_length=32,
        pattern=r"^(#[0-9A-Fa-f]{3,8}|[a-zA-Z][a-zA-Z0-9 ()\-]{2,31})$",
    ),
]
NotificationCategory = Literal[
    "CONTENT_AWAITING_APPROVAL",
    "CONTENT_CHANGES_REQUESTED",
    "CONTENT_APPROVED",
    "STRATEGY_AWAITING_APPROVAL",
    "INVITATION",
    "PROCESSING_FAILED",
    "PUBLICATION_RECORDED",
    "REPORT_AVAILABLE",
]


def _validate_timezone(value: str) -> str:
    normalized = value.strip()
    try:
        ZoneInfo(normalized)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError("timezone deve usar um identificador IANA válido") from exc
    return normalized


def _unique_values(values: list[Any], *, label: str) -> list[Any]:
    normalized = [str(value).strip().casefold() for value in values]
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label} não aceita itens repetidos")
    return values


class OnboardingInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RevisionedStep(OnboardingInput):
    revision: int = Field(ge=1)


class CompanyStep(RevisionedStep):
    step: Literal[1]
    name: Annotated[str, StringConstraints(min_length=2, max_length=200)]
    brand_name: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    public_name: str = Field(default="", max_length=200)
    description: LongText = ""
    timezone: str = Field(default="America/Sao_Paulo", min_length=1, max_length=64)

    _timezone_is_valid = field_validator("timezone")(_validate_timezone)


class SegmentStep(RevisionedStep):
    step: Literal[2]
    segment: Annotated[str, StringConstraints(min_length=2, max_length=120)]


class ServiceInput(OnboardingInput):
    id: UUID | None = None
    name: ShortText
    description: LongText = ""
    category: str = Field(default="", max_length=120)
    warnings: list[RuleText] = Field(default_factory=list, max_length=30)


class ServicesStep(RevisionedStep):
    step: Literal[3]
    services: list[ServiceInput] = Field(min_length=1, max_length=50)

    @field_validator("services")
    @classmethod
    def unique_services(cls, value: list[ServiceInput]) -> list[ServiceInput]:
        _unique_values([item.id or item.name for item in value], label="services")
        return value


class AudienceInput(OnboardingInput):
    id: UUID | None = None
    name: ShortText
    description: LongText = ""
    needs: list[RuleText] = Field(default_factory=list, max_length=50)
    objections: list[RuleText] = Field(default_factory=list, max_length=50)
    location: str = Field(default="", max_length=240)


class AudiencesStep(RevisionedStep):
    step: Literal[4]
    audiences: list[AudienceInput] = Field(min_length=1, max_length=50)

    @field_validator("audiences")
    @classmethod
    def unique_audiences(cls, value: list[AudienceInput]) -> list[AudienceInput]:
        _unique_values([item.id or item.name for item in value], label="audiences")
        return value


class ObjectiveInput(OnboardingInput):
    id: UUID | None = None
    name: ShortText
    description: LongText = ""
    planned_indicators: list[RuleText] = Field(default_factory=list, max_length=30)


class ObjectivesStep(RevisionedStep):
    step: Literal[5]
    objectives: list[ObjectiveInput] = Field(min_length=1, max_length=50)

    @field_validator("objectives")
    @classmethod
    def unique_objectives(cls, value: list[ObjectiveInput]) -> list[ObjectiveInput]:
        _unique_values([item.id or item.name for item in value], label="objectives")
        return value


class DifferentiatorsStep(RevisionedStep):
    step: Literal[6]
    differentiators: list[RuleText] = Field(min_length=1, max_length=50)

    @field_validator("differentiators")
    @classmethod
    def unique_differentiators(cls, value: list[str]) -> list[str]:
        return _unique_values(value, label="differentiators")


class ToneOfVoiceStep(RevisionedStep):
    step: Literal[7]
    tone_of_voice: Annotated[str, StringConstraints(min_length=2, max_length=4000)]
    preferred_words: list[RuleText] = Field(default_factory=list, max_length=50)
    forbidden_words: list[RuleText] = Field(default_factory=list, max_length=50)


class LogosStep(RevisionedStep):
    step: Literal[8]
    logo_media_asset_ids: list[UUID] = Field(min_length=1, max_length=20)

    @field_validator("logo_media_asset_ids")
    @classmethod
    def unique_logos(cls, value: list[UUID]) -> list[UUID]:
        return _unique_values(value, label="logo_media_asset_ids")


class ColorsAndFontsStep(RevisionedStep):
    step: Literal[9]
    primary_colors: list[ColorValue] = Field(min_length=1, max_length=20)
    secondary_colors: list[ColorValue] = Field(default_factory=list, max_length=20)
    fonts: list[ShortText] = Field(min_length=1, max_length=20)


class VisualReferencesStep(RevisionedStep):
    step: Literal[10]
    visual_reference_media_asset_ids: list[UUID] = Field(min_length=1, max_length=50)

    @field_validator("visual_reference_media_asset_ids")
    @classmethod
    def unique_references(cls, value: list[UUID]) -> list[UUID]:
        return _unique_values(value, label="visual_reference_media_asset_ids")


class BrandRulesStep(RevisionedStep):
    step: Literal[11]
    allowed_rules: list[RuleText] = Field(min_length=1, max_length=50)
    forbidden_rules: list[RuleText] = Field(min_length=1, max_length=50)
    required_terms: list[RuleText] = Field(default_factory=list, max_length=50)
    legal_rules: list[RuleText] = Field(default_factory=list, max_length=50)
    image_restrictions: list[RuleText] = Field(default_factory=list, max_length=50)


class ApproversStep(RevisionedStep):
    step: Literal[12]
    membership_ids: list[UUID] = Field(min_length=1, max_length=50)

    @field_validator("membership_ids")
    @classmethod
    def unique_memberships(cls, value: list[UUID]) -> list[UUID]:
        return _unique_values(value, label="membership_ids")


class NotificationSettingsStep(RevisionedStep):
    step: Literal[13]
    email_enabled: bool = True
    mode: Literal["IMMEDIATE", "DAILY", "WEEKLY", "URGENT_ONLY"] = "IMMEDIATE"
    timezone: str = Field(default="America/Sao_Paulo", min_length=1, max_length=64)
    digest_time: time = time(hour=9)
    weekly_day: int = Field(default=1, ge=0, le=6)
    disabled_categories: list[NotificationCategory] = Field(default_factory=list, max_length=8)

    _timezone_is_valid = field_validator("timezone")(_validate_timezone)

    @field_validator("disabled_categories")
    @classmethod
    def unique_categories(cls, value: list[str]) -> list[str]:
        return _unique_values(value, label="disabled_categories")


class InitialPresetStep(RevisionedStep):
    step: Literal[14]
    preset_id: UUID | None = None
    preset: VisualPresetCreate | None = None

    @model_validator(mode="after")
    def require_exactly_one_preset_source(self) -> "InitialPresetStep":
        if (self.preset_id is None) == (self.preset is None):
            raise ValueError("informe preset_id ou preset, mas não ambos")
        return self


class FinalReviewStep(RevisionedStep):
    step: Literal[15]
    confirmed: Literal[True]
    notes: str = Field(default="", max_length=4000)


type OnboardingStepPayload = Annotated[
    CompanyStep
    | SegmentStep
    | ServicesStep
    | AudiencesStep
    | ObjectivesStep
    | DifferentiatorsStep
    | ToneOfVoiceStep
    | LogosStep
    | ColorsAndFontsStep
    | VisualReferencesStep
    | BrandRulesStep
    | ApproversStep
    | NotificationSettingsStep
    | InitialPresetStep
    | FinalReviewStep,
    Field(discriminator="step"),
]


class OnboardingCompleteRequest(OnboardingInput):
    revision: int = Field(ge=1)


class OnboardingSummary(OnboardingInput):
    business_id: UUID
    brand_profile_id: UUID | None
    service_ids: list[UUID]
    audience_ids: list[UUID]
    objective_ids: list[UUID]
    logo_media_asset_ids: list[UUID]
    visual_reference_media_asset_ids: list[UUID]
    approver_membership_ids: list[UUID]
    initial_preset_id: UUID | None
    notification_settings_configured: bool


class BusinessOnboardingRead(OnboardingInput):
    id: UUID
    organization_id: UUID
    business_id: UUID
    status: Literal["IN_PROGRESS", "COMPLETED"]
    current_step: int = Field(ge=1, le=15)
    completed_steps: list[int]
    missing_steps: list[int]
    progress_percent: int = Field(ge=0, le=100)
    revision: int = Field(ge=1)
    step_data: dict[str, dict[str, Any]]
    summary: OnboardingSummary
    started_by_user_id: UUID
    updated_by_user_id: UUID
    completed_by_user_id: UUID | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
