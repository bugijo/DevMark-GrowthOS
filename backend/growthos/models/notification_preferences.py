from datetime import datetime, time
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from growthos.domain.enums import (
    NotificationCategory,
    NotificationDeliveryMode,
    NotificationDeliveryStatus,
    NotificationDigestFrequency,
    NotificationDigestStatus,
)
from growthos.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class NotificationPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_notification_preference_org_user",
        ),
        UniqueConstraint(
            "id",
            "organization_id",
            "user_id",
            name="uq_notification_preference_tenant_identity",
        ),
        CheckConstraint(
            "weekly_day >= 0 AND weekly_day <= 6",
            name="ck_notification_preference_weekly_day",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo", nullable=False)
    digest_time: Mapped[time] = mapped_column(nullable=False, default=time(hour=9))
    weekly_day: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class NotificationCategoryPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_category_preferences"
    __table_args__ = (
        ForeignKeyConstraint(
            ["preference_id", "organization_id", "user_id"],
            [
                "notification_preferences.id",
                "notification_preferences.organization_id",
                "notification_preferences.user_id",
            ],
            ondelete="CASCADE",
            name="fk_notification_category_preference_tenant",
        ),
        UniqueConstraint(
            "organization_id",
            "user_id",
            "category",
            name="uq_notification_category_org_user",
        ),
        Index(
            "ix_notification_category_pref_digest",
            "organization_id",
            "user_id",
            "delivery_mode",
            "is_enabled",
        ),
    )

    preference_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    category: Mapped[NotificationCategory] = mapped_column(
        Enum(NotificationCategory, native_enum=False, length=80), nullable=False
    )
    delivery_mode: Mapped[NotificationDeliveryMode] = mapped_column(
        Enum(NotificationDeliveryMode, native_enum=False, length=24),
        default=NotificationDeliveryMode.IMMEDIATE,
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class NotificationDigest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_digests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["preference_id", "organization_id", "user_id"],
            [
                "notification_preferences.id",
                "notification_preferences.organization_id",
                "notification_preferences.user_id",
            ],
            ondelete="CASCADE",
            name="fk_notification_digest_preference_tenant",
        ),
        UniqueConstraint(
            "id",
            "organization_id",
            "user_id",
            name="uq_notification_digest_tenant_identity",
        ),
        UniqueConstraint(
            "organization_id",
            "user_id",
            "frequency",
            "period_end",
            name="uq_notification_digest_slot",
        ),
        CheckConstraint(
            "period_start < period_end",
            name="ck_notification_digest_period",
        ),
        CheckConstraint(
            "notification_count >= 0",
            name="ck_notification_digest_count",
        ),
        Index(
            "ix_notification_digest_user_period",
            "organization_id",
            "user_id",
            "period_end",
        ),
    )

    preference_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    frequency: Mapped[NotificationDigestFrequency] = mapped_column(
        Enum(NotificationDigestFrequency, native_enum=False, length=16), nullable=False
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[NotificationDigestStatus] = mapped_column(
        Enum(NotificationDigestStatus, native_enum=False, length=16),
        default=NotificationDigestStatus.PENDING,
        nullable=False,
    )
    notification_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class NotificationDigestItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notification_digest_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["digest_id", "organization_id", "user_id"],
            [
                "notification_digests.id",
                "notification_digests.organization_id",
                "notification_digests.user_id",
            ],
            ondelete="CASCADE",
            name="fk_notification_digest_item_digest_tenant",
        ),
        ForeignKeyConstraint(
            ["notification_id", "organization_id", "user_id"],
            [
                "notifications.id",
                "notifications.organization_id",
                "notifications.recipient_user_id",
            ],
            ondelete="CASCADE",
            name="fk_notification_digest_item_notification_tenant",
        ),
        UniqueConstraint(
            "digest_id",
            "notification_id",
            name="uq_notification_digest_item",
        ),
    )

    digest_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    notification_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class NotificationDelivery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["notification_id", "organization_id", "user_id"],
            [
                "notifications.id",
                "notifications.organization_id",
                "notifications.recipient_user_id",
            ],
            ondelete="CASCADE",
            name="fk_notification_delivery_notification_tenant",
        ),
        ForeignKeyConstraint(
            ["digest_id", "organization_id", "user_id"],
            [
                "notification_digests.id",
                "notification_digests.organization_id",
                "notification_digests.user_id",
            ],
            ondelete="CASCADE",
            name="fk_notification_delivery_digest_tenant",
        ),
        CheckConstraint(
            "(notification_id IS NOT NULL AND digest_id IS NULL) OR "
            "(notification_id IS NULL AND digest_id IS NOT NULL)",
            name="ck_notification_delivery_source",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_notification_delivery_attempt_count",
        ),
        UniqueConstraint(
            "organization_id",
            "notification_id",
            "channel",
            name="uq_notification_delivery_notification_channel",
        ),
        UniqueConstraint(
            "organization_id",
            "digest_id",
            "channel",
            name="uq_notification_delivery_digest_channel",
        ),
        Index(
            "ix_notification_delivery_user_created",
            "organization_id",
            "user_id",
            "created_at",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    notification_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    digest_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    channel: Mapped[str] = mapped_column(String(24), default="EMAIL", nullable=False)
    delivery_mode: Mapped[NotificationDeliveryMode] = mapped_column(
        Enum(NotificationDeliveryMode, native_enum=False, length=24), nullable=False
    )
    status: Mapped[NotificationDeliveryStatus] = mapped_column(
        Enum(NotificationDeliveryStatus, native_enum=False, length=24), nullable=False
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
