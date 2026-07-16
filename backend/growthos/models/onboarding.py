from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from growthos.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BusinessOnboarding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_onboardings"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "business_id",
            name="uq_business_onboarding_org_business",
        ),
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'COMPLETED')",
            name="ck_business_onboarding_record_status",
        ),
        CheckConstraint(
            "current_step >= 1 AND current_step <= 15",
            name="ck_business_onboarding_current_step",
        ),
        CheckConstraint("revision > 0", name="ck_business_onboarding_revision_positive"),
        Index("ix_business_onboardings_org_status", "organization_id", "status"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), default="IN_PROGRESS", nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    completed_steps: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    step_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    started_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    completed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
