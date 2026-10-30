from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
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

from growthos.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LandingPage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Página de captação de um negócio cliente; só fica pública após aprovação humana."""

    __tablename__ = "landing_pages"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','APPROVED')", name="ck_landing_page_status"),
        UniqueConstraint("business_id", name="uq_landing_page_business"),
        UniqueConstraint("slug", name="uq_landing_page_slug"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    headline: Mapped[str] = mapped_column(String(200), nullable=False)
    subheadline: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cta_label: Mapped[str] = mapped_column(String(80), nullable=False)
    address: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    contact_channel: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    # Número oficial do estabelecimento (só dígitos, com DDI); vazio esconde o botão.
    whatsapp_number: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    highlights: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    service_options: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    price_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    price_disclaimer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    demo_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BusinessLead(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Interessado no serviço de um negócio cliente (ex.: tutor pedindo banho e tosa)."""

    __tablename__ = "business_leads"
    __table_args__ = (
        CheckConstraint(
            "source IN ('LANDING_DEMO','LANDING_PAGE','INSTAGRAM_POST','INSTAGRAM_STORY',"
            "'INDICACAO','WHATSAPP_DIRETO','OUTRO')",
            name="ck_business_lead_source",
        ),
        CheckConstraint(
            "status IN ('NOVO','AGUARDANDO_DADOS','HORARIO_OFERTADO','CONFIRMADO','REALIZADO',"
            "'CANCELADO','NAO_COMPARECEU')",
            name="ck_business_lead_status",
        ),
        Index("ix_business_leads_business_status", "business_id", "status", "created_at"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    landing_page_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("landing_pages.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="NOVO")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    service_requested: Mapped[str] = mapped_column(String(120), nullable=False)
    price_item_label: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    reference_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_period: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    next_action: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    next_action_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Dados de contato só existem em pedidos reais, aceitos com aviso aprovado.
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    privacy_notice_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consent_recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LeadPrivacySettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Aviso de privacidade e regras de tratamento dos pedidos de um estabelecimento.

    APPROVED significa apenas que o responsável pelo estabelecimento revisou e
    aprovou o texto; não é uma declaração de conformidade legal.
    """

    __tablename__ = "lead_privacy_settings"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','APPROVED')", name="ck_lead_privacy_status"),
        CheckConstraint(
            "legal_basis IN ('CONSENTIMENTO','PROCEDIMENTOS_PRELIMINARES','LEGITIMO_INTERESSE')",
            name="ck_lead_privacy_legal_basis",
        ),
        CheckConstraint("retention_days BETWEEN 1 AND 730", name="ck_lead_privacy_retention"),
        UniqueConstraint("business_id", name="uq_lead_privacy_business"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    controller_name: Mapped[str] = mapped_column(String(200), nullable=False)
    privacy_contact: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(32), nullable=False)
    data_categories: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    notice_text: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_note: Mapped[str] = mapped_column(Text, nullable=False, default="")


class BusinessAvailability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Janelas semanais de atendimento informadas pelo estabelecimento (vazia por padrão)."""

    __tablename__ = "business_availability"
    __table_args__ = (UniqueConstraint("business_id", name="uq_business_availability_business"),)

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    slots: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confirmed_by_business: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class LandingDailyMetric(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Contagem agregada por dia de eventos da landing (ex.: clique no WhatsApp).

    Não guarda IP, cookie, identificador nem conteúdo da conversa: um clique não é
    um interessado nem um agendamento.
    """

    __tablename__ = "landing_daily_metrics"
    __table_args__ = (
        CheckConstraint("event IN ('whatsapp_click')", name="ck_landing_metric_event"),
        UniqueConstraint("landing_page_id", "day", "event", name="uq_landing_metric_day_event"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    landing_page_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("landing_pages.id", ondelete="CASCADE"), nullable=False
    )
    day: Mapped[date] = mapped_column(Date, nullable=False)
    event: Mapped[str] = mapped_column(String(32), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
