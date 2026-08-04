from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from growthos.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Business(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "businesses"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_business_org_name"),
        CheckConstraint(
            "onboarding_status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED')",
            name="ck_business_onboarding_status",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    segment: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo", nullable=False)
    onboarding_status: Mapped[str] = mapped_column(
        String(24), default="NOT_STARTED", nullable=False
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BrandProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "brand_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "business_id", name="uq_brand_org_business"),
        CheckConstraint("version > 0", name="ck_brand_profile_version_positive"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    brand_name: Mapped[str] = mapped_column(String(200), nullable=False)
    public_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    segment: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    audience: Mapped[str] = mapped_column(Text, default="", nullable=False)
    primary_colors: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    secondary_colors: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    fonts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    logo_media_asset_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    visual_reference_media_asset_ids: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    tone_of_voice: Mapped[str] = mapped_column(Text, default="", nullable=False)
    preferred_words: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    forbidden_words: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    slogan: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    differentiators: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    services: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    contacts: Mapped[dict[str, Any] | str | None] = mapped_column(JSON, nullable=True)
    links: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    calls_to_action: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    allowed_rules: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    forbidden_rules: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    required_terms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    legal_rules: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    image_restrictions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    internal_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
