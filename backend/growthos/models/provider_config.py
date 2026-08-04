from datetime import datetime
from uuid import UUID

from sqlalchemy import (
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

from growthos.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProviderConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "provider_configs"
    __table_args__ = (
        CheckConstraint("priority >= 0", name="ck_provider_config_priority"),
        CheckConstraint("timeout_seconds BETWEEN 1 AND 120", name="ck_provider_config_timeout"),
        CheckConstraint("max_attempts BETWEEN 1 AND 10", name="ck_provider_config_attempts"),
        UniqueConstraint(
            "organization_id", "kind", "provider", name="uq_provider_config_org_kind_provider"
        ),
        Index("ix_provider_configs_org_kind_priority", "organization_id", "kind", "priority"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    fallback_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    test_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    secret_environment_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str] = mapped_column(String(32), default="NOT_CHECKED", nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
