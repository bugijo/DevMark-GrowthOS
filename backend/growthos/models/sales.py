from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from growthos.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SalesLead(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sales_leads"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('NEW_LEAD','CONTACT_PENDING','BRIEFING','PROPOSAL_PREPARATION',"
            "'PROPOSAL_SENT','NEGOTIATION','CONTRACTED','IN_PRODUCTION','DELIVERED','AFTER_SALES')",
            name="ck_sales_lead_stage",
        ),
        CheckConstraint("source IN ('PUBLIC_FORM','MANUAL','TEST')", name="ck_sales_lead_source"),
        CheckConstraint(
            "service_classification IN ('IN_SCOPE_LANDING_PAGE','OUT_OF_SCOPE','HUMAN_REVIEW')",
            name="ck_sales_lead_service_classification",
        ),
        UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_sales_lead_org_idempotency"
        ),
        Index("ix_sales_leads_org_stage_created", "organization_id", "stage", "created_at"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="NEW_LEAD")
    service_classification: Mapped[str] = mapped_column(
        String(32), nullable=False, default="HUMAN_REVIEW"
    )
    classification_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    company: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    whatsapp: Mapped[str] = mapped_column(String(24), nullable=False, default="")
    business_type: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    desired_timeline: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    additional_info: Mapped[str] = mapped_column(Text, nullable=False, default="")
    privacy_notice_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proposal_draft: Mapped[str | None] = mapped_column(Text, nullable=True)


class SalesLeadTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sales_lead_tasks"
    __table_args__ = (Index("ix_sales_lead_tasks_org_due", "organization_id", "due_at"),)

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    lead_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sales_leads.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
