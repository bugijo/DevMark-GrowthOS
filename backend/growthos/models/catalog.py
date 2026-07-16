from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from growthos.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Service(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "services"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "business_id",
            "name",
            name="uq_service_org_business_name",
        ),
        Index("ix_services_org_business_active", "organization_id", "business_id", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AudienceSegment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audience_segments"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "business_id",
            "name",
            name="uq_audience_segment_org_business_name",
        ),
        Index(
            "ix_audience_segments_org_business_active",
            "organization_id",
            "business_id",
            "is_active",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    needs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    objections: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    location: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MarketingObjective(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "marketing_objectives"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "business_id",
            "name",
            name="uq_marketing_objective_org_business_name",
        ),
        Index(
            "ix_marketing_objectives_org_business_active",
            "organization_id",
            "business_id",
            "is_active",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    planned_indicators: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MediaAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        UniqueConstraint("organization_id", "object_key", name="uq_media_asset_org_object_key"),
        CheckConstraint("byte_size >= 0", name="ck_media_asset_byte_size_non_negative"),
        CheckConstraint(
            "processing_status IN ('PENDING', 'READY', 'REJECTED', 'FAILED', 'ARCHIVED')",
            name="ck_media_asset_processing_status",
        ),
        Index(
            "ix_media_assets_org_business_created",
            "organization_id",
            "business_id",
            "created_at",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(40), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    display_name: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin: Mapped[str] = mapped_column(String(40), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False)
    metadata_safe: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VisualPreset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "visual_presets"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "business_id",
            "name",
            name="uq_visual_preset_org_business_name",
        ),
        CheckConstraint(
            "creation_mode IN ('TEMPLATE', 'AI_IMAGE', 'HYBRID', 'MANUAL')",
            name="ck_visual_preset_creation_mode",
        ),
        CheckConstraint("version > 0", name="ck_visual_preset_version_positive"),
        CheckConstraint(
            "logo_scale_percent IS NULL OR (logo_scale_percent >= 1 AND logo_scale_percent <= 100)",
            name="ck_visual_preset_logo_scale_percent",
        ),
        CheckConstraint(
            "max_text_characters IS NULL OR max_text_characters >= 0",
            name="ck_visual_preset_max_text_characters",
        ),
        Index(
            "ix_visual_presets_org_business_active",
            "organization_id",
            "business_id",
            "is_active",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    brand_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("brand_profiles.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    format: Mapped[str] = mapped_column(String(80), nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(20), nullable=False)
    creation_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    color_palette: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    fonts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    logo_media_asset_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    logo_position: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    logo_scale_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safe_margins: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    background_style: Mapped[str] = mapped_column(Text, default="", nullable=False)
    photographic_style: Mapped[str] = mapped_column(Text, default="", nullable=False)
    realism_level: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    lighting: Mapped[str] = mapped_column(Text, default="", nullable=False)
    composition: Mapped[str] = mapped_column(Text, default="", nullable=False)
    max_text_characters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_rules: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    base_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    negative_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    allowed_elements: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    forbidden_elements: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    visual_signature: Mapped[str] = mapped_column(Text, default="", nullable=False)
    default_cta: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ContentVersionMedia(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "content_version_media"
    __table_args__ = (
        UniqueConstraint(
            "content_version_id",
            "media_asset_id",
            "role",
            name="uq_content_version_media_role",
        ),
        CheckConstraint(
            "role IN ('PRIMARY', 'REFERENCE', 'BACKGROUND', 'OUTPUT')",
            name="ck_content_version_media_role",
        ),
        CheckConstraint("sort_order >= 0", name="ck_content_version_media_sort_order"),
        Index(
            "ix_content_version_media_org_business",
            "organization_id",
            "business_id",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    content_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_versions.id", ondelete="CASCADE"), nullable=False
    )
    media_asset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media_assets.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
