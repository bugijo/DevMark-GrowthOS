"""Adiciona estratégia versionada, planos e calendário editorial.

Revision ID: 0006_strategy_calendar
Revises: 0005_catalogs_media
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_strategy_calendar"
down_revision: str | None = "0005_catalogs_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "content_strategies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("approved_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("starts_on <= ends_on", name="ck_content_strategy_period"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'INTERNAL_REVIEW', 'CLIENT_REVIEW', 'APPROVED', 'ARCHIVED')",
            name="ck_content_strategy_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "business_id",
            "name",
            "starts_on",
            "ends_on",
            name="uq_content_strategy_org_business_period_name",
        ),
    )
    op.create_index(
        "ix_content_strategies_org_business_period",
        "content_strategies",
        ["organization_id", "business_id", "starts_on", "ends_on"],
    )

    op.create_table(
        "strategy_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("content_strategy_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("positioning", sa.Text(), nullable=False),
        sa.Column("funnel", sa.JSON(), nullable=False),
        sa.Column("channels", sa.JSON(), nullable=False),
        sa.Column("pillars", sa.JSON(), nullable=False),
        sa.Column("planned_indicators", sa.JSON(), nullable=False),
        sa.Column("service_snapshots", sa.JSON(), nullable=False),
        sa.Column("audience_snapshots", sa.JSON(), nullable=False),
        sa.Column("objective_snapshots", sa.JSON(), nullable=False),
        sa.Column("brand_context_snapshot", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=False),
        sa.Column("provider_reference", sa.String(length=160), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["content_strategy_id"], ["content_strategies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id"], ["strategy_versions.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint("version_number > 0", name="ck_strategy_version_number_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_strategy_id", "version_number", name="uq_strategy_version_number"
        ),
    )
    op.create_index(
        "ix_strategy_versions_org_business_strategy",
        "strategy_versions",
        ["organization_id", "business_id", "content_strategy_id"],
    )
    op.create_foreign_key(
        "fk_content_strategy_current_version",
        "content_strategies",
        "strategy_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_content_strategy_approved_version",
        "content_strategies",
        "strategy_versions",
        ["approved_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "content_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("content_strategy_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_version_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("frequency", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["content_strategy_id"], ["content_strategies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["strategy_version_id"], ["strategy_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.CheckConstraint("starts_on <= ends_on", name="ck_content_plan_period"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'COMPLETED', 'ARCHIVED')",
            name="ck_content_plan_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "business_id",
            "name",
            "starts_on",
            "ends_on",
            name="uq_content_plan_org_business_period_name",
        ),
    )
    op.create_index(
        "ix_content_plans_org_business_period",
        "content_plans",
        ["organization_id", "business_id", "starts_on", "ends_on"],
    )

    op.create_table(
        "calendar_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("content_plan_id", sa.Uuid(), nullable=False),
        sa.Column("content_item_id", sa.Uuid(), nullable=True),
        sa.Column("visual_preset_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("audience", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(length=80), nullable=False),
        sa.Column("format", sa.String(length=80), nullable=False),
        sa.Column("suggested_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["content_item_id"], ["content_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_plan_id"], ["content_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["visual_preset_id"], ["visual_presets.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('PLANNED', 'GENERATED', 'SCHEDULED', 'PUBLISHED', 'ARCHIVED')",
            name="ck_calendar_entry_status",
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_calendar_entry_sort_order"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_calendar_entries_org_business_suggested",
        "calendar_entries",
        ["organization_id", "business_id", "suggested_for"],
    )
    op.create_index(
        "ix_calendar_entries_plan_suggested",
        "calendar_entries",
        ["content_plan_id", "suggested_for"],
    )


def downgrade() -> None:
    op.drop_table("calendar_entries")
    op.drop_table("content_plans")
    op.drop_constraint(
        "fk_content_strategy_approved_version",
        "content_strategies",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_content_strategy_current_version",
        "content_strategies",
        type_="foreignkey",
    )
    op.drop_table("strategy_versions")
    op.drop_table("content_strategies")
