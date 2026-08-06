from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from growthos.domain.enums import ProfessionalReviewDecision
from growthos.models.base import Base, UUIDPrimaryKeyMixin, utcnow


class ProfessionalContentReview(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "professional_content_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('APPROVED', 'CHANGES_REQUESTED')",
            name="ck_professional_review_decision",
        ),
        ForeignKeyConstraint(
            ["content_version_id", "organization_id", "business_id", "content_item_id"],
            [
                "content_versions.id",
                "content_versions.organization_id",
                "content_versions.business_id",
                "content_versions.content_item_id",
            ],
            name="fk_professional_review_version_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["reviewer_membership_id", "organization_id", "reviewer_user_id"],
            ["memberships.id", "memberships.organization_id", "memberships.user_id"],
            name="fk_professional_review_membership_tenant",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "organization_id",
            "content_version_id",
            name="uq_professional_review_version",
        ),
        Index(
            "ix_professional_review_content_created",
            "organization_id",
            "business_id",
            "content_item_id",
            "created_at",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    business_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    content_item_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    content_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    reviewer_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    reviewer_membership_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    decision: Mapped[ProfessionalReviewDecision] = mapped_column(
        Enum(ProfessionalReviewDecision, native_enum=False, length=32), nullable=False
    )
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
