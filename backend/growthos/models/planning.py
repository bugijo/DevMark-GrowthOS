from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
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


class ContentStrategy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_strategies"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "business_id",
            "name",
            "starts_on",
            "ends_on",
            name="uq_content_strategy_org_business_period_name",
        ),
        CheckConstraint("starts_on <= ends_on", name="ck_content_strategy_period"),
        CheckConstraint(
            "status IN ('DRAFT', 'INTERNAL_REVIEW', 'CLIENT_REVIEW', 'APPROVED', 'ARCHIVED')",
            name="ck_content_strategy_status",
        ),
        Index(
            "ix_content_strategies_org_business_period",
            "organization_id",
            "business_id",
            "starts_on",
            "ends_on",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", nullable=False)
    current_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "strategy_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_content_strategy_current_version",
        ),
        nullable=True,
    )
    approved_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "strategy_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_content_strategy_approved_version",
        ),
        nullable=True,
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    submitted_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StrategyVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "strategy_versions"
    __table_args__ = (
        UniqueConstraint(
            "content_strategy_id",
            "version_number",
            name="uq_strategy_version_number",
        ),
        CheckConstraint("version_number > 0", name="ck_strategy_version_number_positive"),
        Index(
            "ix_strategy_versions_org_business_strategy",
            "organization_id",
            "business_id",
            "content_strategy_id",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    content_strategy_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_strategies.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    positioning: Mapped[str] = mapped_column(Text, default="", nullable=False)
    funnel: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    channels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    pillars: Mapped[list[dict[str, Any] | str]] = mapped_column(JSON, default=list, nullable=False)
    planned_indicators: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    service_snapshots: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    audience_snapshots: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    objective_snapshots: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    brand_context_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_reference: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    supersedes_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("strategy_versions.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ContentPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_plans"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "business_id",
            "name",
            "starts_on",
            "ends_on",
            name="uq_content_plan_org_business_period_name",
        ),
        CheckConstraint("starts_on <= ends_on", name="ck_content_plan_period"),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'COMPLETED', 'ARCHIVED')",
            name="ck_content_plan_status",
        ),
        Index(
            "ix_content_plans_org_business_period",
            "organization_id",
            "business_id",
            "starts_on",
            "ends_on",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    content_strategy_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_strategies.id", ondelete="RESTRICT"), nullable=False
    )
    strategy_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("strategy_versions.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    frequency: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CalendarEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "calendar_entries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PLANNED', 'GENERATED', 'SCHEDULED', 'PUBLISHED', 'ARCHIVED')",
            name="ck_calendar_entry_status",
        ),
        CheckConstraint("sort_order >= 0", name="ck_calendar_entry_sort_order"),
        Index(
            "ix_calendar_entries_org_business_suggested",
            "organization_id",
            "business_id",
            "suggested_for",
        ),
        Index("ix_calendar_entries_plan_suggested", "content_plan_id", "suggested_for"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    content_plan_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_plans.id", ondelete="CASCADE"), nullable=False
    )
    content_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True
    )
    visual_preset_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("visual_presets.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(Text, default="", nullable=False)
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    format: Mapped[str] = mapped_column(String(80), nullable=False)
    suggested_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="PLANNED", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
