from datetime import datetime
from typing import Annotated, ClassVar, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=300),
]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10_000)]
ListItem = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
CreationMode = Literal["TEMPLATE", "AI_IMAGE", "HYBRID", "MANUAL"]


class CatalogSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CatalogReadSchema(CatalogSchema):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    organization_id: UUID
    business_id: UUID
    is_active: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CatalogUpdateSchema(CatalogSchema):
    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def require_at_least_one_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("informe ao menos uma alteração")
        invalid_nulls = sorted(
            field
            for field in self.model_fields_set
            if getattr(self, field) is None and field not in self.nullable_fields
        )
        if invalid_nulls:
            raise ValueError("campos não aceitam valor nulo: " + ", ".join(invalid_nulls))
        return self


class ServiceCreate(CatalogSchema):
    name: ShortText
    description: LongText = ""
    category: ShortText | None = None
    warnings: list[ListItem] = Field(default_factory=list, max_length=30)


class ServiceUpdate(CatalogUpdateSchema):
    nullable_fields = frozenset({"category"})

    name: ShortText | None = None
    description: LongText | None = None
    category: ShortText | None = None
    warnings: list[ListItem] | None = Field(default=None, max_length=30)


class ServiceRead(ServiceCreate, CatalogReadSchema):
    category: str = ""


class AudienceSegmentCreate(CatalogSchema):
    name: ShortText
    description: LongText = ""
    needs: list[ListItem] = Field(default_factory=list, max_length=50)
    objections: list[ListItem] = Field(default_factory=list, max_length=50)
    location: ShortText | None = None


class AudienceSegmentUpdate(CatalogUpdateSchema):
    nullable_fields = frozenset({"location"})

    name: ShortText | None = None
    description: LongText | None = None
    needs: list[ListItem] | None = Field(default=None, max_length=50)
    objections: list[ListItem] | None = Field(default=None, max_length=50)
    location: ShortText | None = None


class AudienceSegmentRead(AudienceSegmentCreate, CatalogReadSchema):
    location: str = ""


class MarketingObjectiveCreate(CatalogSchema):
    name: ShortText
    description: LongText = ""
    planned_indicators: list[ListItem] = Field(default_factory=list, max_length=30)


class MarketingObjectiveUpdate(CatalogUpdateSchema):
    name: ShortText | None = None
    description: LongText | None = None
    planned_indicators: list[ListItem] | None = Field(default=None, max_length=30)


class MarketingObjectiveRead(MarketingObjectiveCreate, CatalogReadSchema):
    pass


class VisualPresetCreate(CatalogSchema):
    name: ShortText
    objective: LongText = ""
    format: ShortText
    aspect_ratio: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=2, max_length=20),
    ]
    creation_mode: CreationMode
    color_palette: list[ListItem] = Field(default_factory=list, max_length=30)
    fonts: list[ListItem] = Field(default_factory=list, max_length=20)
    logo_media_asset_id: UUID | None = None
    logo_position: str = Field(default="", max_length=80)
    logo_scale_percent: int | None = Field(default=None, ge=1, le=100)
    safe_margins: dict[str, float] = Field(default_factory=dict)
    background_style: LongText = ""
    photographic_style: LongText = ""
    realism_level: str = Field(default="", max_length=80)
    lighting: LongText = ""
    composition: LongText = ""
    max_text_characters: int | None = Field(default=None, ge=0, le=10_000)
    text_rules: list[ListItem] = Field(default_factory=list, max_length=50)
    base_prompt: LongText = ""
    negative_prompt: LongText = ""
    allowed_elements: list[ListItem] = Field(default_factory=list, max_length=50)
    forbidden_elements: list[ListItem] = Field(default_factory=list, max_length=50)
    visual_signature: LongText = ""
    default_cta: str = Field(default="", max_length=300)


class VisualPresetUpdate(CatalogUpdateSchema):
    nullable_fields = frozenset(
        {"logo_media_asset_id", "logo_scale_percent", "max_text_characters"}
    )

    name: ShortText | None = None
    objective: LongText | None = None
    format: ShortText | None = None
    aspect_ratio: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, min_length=2, max_length=20),
    ] = None
    creation_mode: CreationMode | None = None
    color_palette: list[ListItem] | None = Field(default=None, max_length=30)
    fonts: list[ListItem] | None = Field(default=None, max_length=20)
    logo_media_asset_id: UUID | None = None
    logo_position: str | None = Field(default=None, max_length=80)
    logo_scale_percent: int | None = Field(default=None, ge=1, le=100)
    safe_margins: dict[str, float] | None = None
    background_style: LongText | None = None
    photographic_style: LongText | None = None
    realism_level: str | None = Field(default=None, max_length=80)
    lighting: LongText | None = None
    composition: LongText | None = None
    max_text_characters: int | None = Field(default=None, ge=0, le=10_000)
    text_rules: list[ListItem] | None = Field(default=None, max_length=50)
    base_prompt: LongText | None = None
    negative_prompt: LongText | None = None
    allowed_elements: list[ListItem] | None = Field(default=None, max_length=50)
    forbidden_elements: list[ListItem] | None = Field(default=None, max_length=50)
    visual_signature: LongText | None = None
    default_cta: str | None = Field(default=None, max_length=300)


class VisualPresetRead(VisualPresetCreate, CatalogReadSchema):
    brand_profile_id: UUID
    version: int
    created_by_user_id: UUID
    updated_by_user_id: UUID


class VisualPromptGenerateRequest(CatalogSchema):
    business_id: UUID
    preset_id: UUID
    objective: ShortText
    audience: LongText = ""
    format: str | None = Field(default=None, min_length=2, max_length=80)
    aspect_ratio: str | None = Field(default=None, min_length=2, max_length=20)


class VisualPromptRead(CatalogSchema):
    business_id: UUID
    preset_id: UUID
    preset_version: int
    prompt: str
    negative_prompt: str
    provider_name: str
    provider_reference: str
