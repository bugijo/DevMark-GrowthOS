from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from growthos.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Business(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "businesses"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_business_org_name"),)

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    segment: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BrandProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "brand_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "business_id", name="uq_brand_org_business"),
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
    tone_of_voice: Mapped[str] = mapped_column(Text, default="", nullable=False)
    preferred_words: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    forbidden_words: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    slogan: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    differentiators: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    services: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    contacts: Mapped[dict[str, Any] | str | None] = mapped_column(JSON, nullable=True)
    links: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    calls_to_action: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    internal_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
