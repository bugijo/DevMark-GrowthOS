"""Adiciona preferências, resumos e entregas de notificações.

Revision ID: 0010_phase3_notifications
Revises: 0009_phase3_onboarding
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_phase3_notifications"
down_revision: str | None = "0009_phase3_onboarding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CATEGORIES = (
    "CONTENT_AWAITING_APPROVAL",
    "CONTENT_CHANGES_REQUESTED",
    "CONTENT_APPROVED",
    "STRATEGY_AWAITING_APPROVAL",
    "INVITATION",
    "PROCESSING_FAILED",
    "PUBLICATION_RECORDED",
    "REPORT_AVAILABLE",
)
_MODES = ("IMMEDIATE", "DAILY", "WEEKLY", "URGENT_ONLY")
_DELIVERY_STATUSES = ("PENDING", "PROCESSING", "DELIVERED", "FAILED", "SKIPPED")
_DIGEST_STATUSES = ("PENDING", "EMPTY", "DELIVERED", "FAILED")


def _values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column(
            "category",
            sa.String(length=80),
            server_default="REPORT_AVAILABLE",
            nullable=False,
        ),
    )
    op.add_column(
        "notifications",
        sa.Column(
            "importance",
            sa.String(length=16),
            server_default="NORMAL",
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE notifications
           SET category = CASE type
               WHEN 'CONTENT_REVIEW_REQUESTED' THEN 'CONTENT_AWAITING_APPROVAL'
               WHEN 'CONTENT_DECISION' THEN CASE
                   WHEN LOWER(title) LIKE '%altera%'
                     OR LOWER(message) LIKE '%altera%'
                   THEN 'CONTENT_CHANGES_REQUESTED'
                   ELSE 'CONTENT_APPROVED'
               END
               WHEN 'STRATEGY_REVIEW' THEN 'STRATEGY_AWAITING_APPROVAL'
               WHEN 'STRATEGY_DECISION' THEN CASE
                   WHEN LOWER(title) LIKE '%altera%'
                     OR LOWER(message) LIKE '%altera%'
                   THEN 'CONTENT_CHANGES_REQUESTED'
                   ELSE 'CONTENT_APPROVED'
               END
               WHEN 'INVITATION_ACCEPTED' THEN 'INVITATION'
               ELSE 'REPORT_AVAILABLE'
           END,
               importance = CASE type
                   WHEN 'CONTENT_REVIEW_REQUESTED' THEN 'URGENT'
                   WHEN 'STRATEGY_REVIEW' THEN 'URGENT'
                   ELSE 'NORMAL'
               END
        """
    )
    op.create_check_constraint(
        "ck_notification_category",
        "notifications",
        f"category IN ({_values(_CATEGORIES)})",
    )
    op.create_check_constraint(
        "ck_notification_importance",
        "notifications",
        "importance IN ('NORMAL', 'URGENT')",
    )
    op.create_unique_constraint(
        "uq_notification_tenant_recipient",
        "notifications",
        ["id", "organization_id", "recipient_user_id"],
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("digest_time", sa.Time(), nullable=False),
        sa.Column("weekly_day", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "weekly_day >= 0 AND weekly_day <= 6",
            name="ck_notification_preference_weekly_day",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_notification_preference_org_user",
        ),
        sa.UniqueConstraint(
            "id",
            "organization_id",
            "user_id",
            name="uq_notification_preference_tenant_identity",
        ),
    )
    op.create_index(
        "ix_notification_preferences_organization_id",
        "notification_preferences",
        ["organization_id"],
    )
    op.create_index(
        "ix_notification_preferences_user_id",
        "notification_preferences",
        ["user_id"],
    )

    op.create_table(
        "notification_category_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("preference_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("delivery_mode", sa.String(length=24), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"category IN ({_values(_CATEGORIES)})",
            name="ck_notification_category_preference_category",
        ),
        sa.CheckConstraint(
            f"delivery_mode IN ({_values(_MODES)})",
            name="ck_notification_category_preference_mode",
        ),
        sa.ForeignKeyConstraint(
            ["preference_id", "organization_id", "user_id"],
            [
                "notification_preferences.id",
                "notification_preferences.organization_id",
                "notification_preferences.user_id",
            ],
            name="fk_notification_category_preference_tenant",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            "category",
            name="uq_notification_category_org_user",
        ),
    )
    op.create_index(
        "ix_notification_category_pref_digest",
        "notification_category_preferences",
        ["organization_id", "user_id", "delivery_mode", "is_enabled"],
    )

    op.create_table(
        "notification_digests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("preference_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("frequency", sa.String(length=16), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notification_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "frequency IN ('DAILY', 'WEEKLY')",
            name="ck_notification_digest_frequency",
        ),
        sa.CheckConstraint(
            f"status IN ({_values(_DIGEST_STATUSES)})",
            name="ck_notification_digest_status",
        ),
        sa.CheckConstraint(
            "period_start < period_end",
            name="ck_notification_digest_period",
        ),
        sa.CheckConstraint(
            "notification_count >= 0",
            name="ck_notification_digest_count",
        ),
        sa.ForeignKeyConstraint(
            ["preference_id", "organization_id", "user_id"],
            [
                "notification_preferences.id",
                "notification_preferences.organization_id",
                "notification_preferences.user_id",
            ],
            name="fk_notification_digest_preference_tenant",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "organization_id",
            "user_id",
            name="uq_notification_digest_tenant_identity",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            "frequency",
            "period_end",
            name="uq_notification_digest_slot",
        ),
    )
    op.create_index(
        "ix_notification_digest_user_period",
        "notification_digests",
        ["organization_id", "user_id", "period_end"],
    )

    op.create_table(
        "notification_digest_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("digest_id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["digest_id", "organization_id", "user_id"],
            [
                "notification_digests.id",
                "notification_digests.organization_id",
                "notification_digests.user_id",
            ],
            name="fk_notification_digest_item_digest_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["notification_id", "organization_id", "user_id"],
            [
                "notifications.id",
                "notifications.organization_id",
                "notifications.recipient_user_id",
            ],
            name="fk_notification_digest_item_notification_tenant",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("digest_id", "notification_id", name="uq_notification_digest_item"),
    )

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=True),
        sa.Column("digest_id", sa.Uuid(), nullable=True),
        sa.Column("channel", sa.String(length=24), nullable=False),
        sa.Column("delivery_mode", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("last_error_code", sa.String(length=120), nullable=True),
        sa.Column("job_id", sa.String(length=100), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(notification_id IS NOT NULL AND digest_id IS NULL) OR "
            "(notification_id IS NULL AND digest_id IS NOT NULL)",
            name="ck_notification_delivery_source",
        ),
        sa.CheckConstraint(
            f"delivery_mode IN ({_values(_MODES)})",
            name="ck_notification_delivery_mode",
        ),
        sa.CheckConstraint(
            f"status IN ({_values(_DELIVERY_STATUSES)})",
            name="ck_notification_delivery_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_notification_delivery_attempt_count",
        ),
        sa.ForeignKeyConstraint(
            ["notification_id", "organization_id", "user_id"],
            [
                "notifications.id",
                "notifications.organization_id",
                "notifications.recipient_user_id",
            ],
            name="fk_notification_delivery_notification_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["digest_id", "organization_id", "user_id"],
            [
                "notification_digests.id",
                "notification_digests.organization_id",
                "notification_digests.user_id",
            ],
            name="fk_notification_delivery_digest_tenant",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "notification_id",
            "channel",
            name="uq_notification_delivery_notification_channel",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "digest_id",
            "channel",
            name="uq_notification_delivery_digest_channel",
        ),
    )
    op.create_index(
        "ix_notification_delivery_user_created",
        "notification_deliveries",
        ["organization_id", "user_id", "created_at"],
    )

    op.alter_column("notifications", "category", server_default=None)
    op.alter_column("notifications", "importance", server_default=None)


def downgrade() -> None:
    op.drop_table("notification_deliveries")
    op.drop_table("notification_digest_items")
    op.drop_table("notification_digests")
    op.drop_table("notification_category_preferences")
    op.drop_table("notification_preferences")
    op.drop_constraint("uq_notification_tenant_recipient", "notifications", type_="unique")
    op.drop_constraint("ck_notification_importance", "notifications", type_="check")
    op.drop_constraint("ck_notification_category", "notifications", type_="check")
    op.drop_column("notifications", "importance")
    op.drop_column("notifications", "category")
