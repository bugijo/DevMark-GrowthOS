from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from growthos.domain.enums import ApprovalComponent, ApprovalStage, ApprovalStatus, ContentStatus
from growthos.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class ContentItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_items"
    __table_args__ = (
        UniqueConstraint("calendar_entry_id", name="uq_content_item_calendar_entry"),
        UniqueConstraint(
            "organization_id",
            "publication_idempotency_key",
            name="uq_content_publication_org_idempotency",
        ),
        Index(
            "ix_content_items_org_business_scheduled",
            "organization_id",
            "business_id",
            "scheduled_for",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, native_enum=False, length=40),
        default=ContentStatus.DRAFT,
        index=True,
        nullable=False,
    )
    current_version_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    content_strategy_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("content_strategies.id", ondelete="SET NULL"),
        nullable=True,
    )
    strategy_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("strategy_versions.id", ondelete="SET NULL"), nullable=True
    )
    content_plan_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_plans.id", ondelete="SET NULL"), nullable=True
    )
    calendar_entry_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "calendar_entries.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_content_item_calendar_entry",
        ),
        nullable=True,
    )
    visual_preset_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("visual_presets.id", ondelete="SET NULL"), nullable=True
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publication_channel: Mapped[str | None] = mapped_column(String(80), nullable=True)
    publication_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    publication_idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class ContentVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "content_versions"
    __table_args__ = (
        UniqueConstraint("content_item_id", "version_number", name="uq_content_version_number"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    content_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    format: Mapped[str] = mapped_column(String(80), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(Text, default="", nullable=False)
    cta: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    service_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("services.id", ondelete="SET NULL"), nullable=True
    )
    audience_segment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("audience_segments.id", ondelete="SET NULL"), nullable=True
    )
    marketing_objective_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("marketing_objectives.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    script: Mapped[str] = mapped_column(Text, default="", nullable=False)
    visual_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    negative_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    brand_context_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    visual_preset_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    provider_name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Approval(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approvals"
    __table_args__ = (
        UniqueConstraint(
            "content_version_id",
            "stage",
            "component",
            name="uq_approval_version_stage_component",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    content_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    content_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_versions.id", ondelete="RESTRICT"), index=True
    )
    stage: Mapped[ApprovalStage] = mapped_column(
        Enum(ApprovalStage, native_enum=False, length=20), default=ApprovalStage.CLIENT
    )
    component: Mapped[ApprovalComponent] = mapped_column(
        Enum(ApprovalComponent, native_enum=False, length=20),
        default=ApprovalComponent.TEXT,
        nullable=False,
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, native_enum=False, length=40), default=ApprovalStatus.PENDING
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    decided_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    decision_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
