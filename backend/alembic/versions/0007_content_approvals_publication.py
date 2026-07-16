"""Amplia conteúdo, separa aprovações e registra publicação manual.

Revision ID: 0007_content_editorial
Revises: 0006_strategy_calendar
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_content_editorial"
down_revision: str | None = "0006_strategy_calendar"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("content_items", sa.Column("content_strategy_id", sa.Uuid(), nullable=True))
    op.add_column("content_items", sa.Column("strategy_version_id", sa.Uuid(), nullable=True))
    op.add_column("content_items", sa.Column("content_plan_id", sa.Uuid(), nullable=True))
    op.add_column("content_items", sa.Column("calendar_entry_id", sa.Uuid(), nullable=True))
    op.add_column("content_items", sa.Column("visual_preset_id", sa.Uuid(), nullable=True))
    op.add_column(
        "content_items",
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "content_items",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "content_items",
        sa.Column("publication_channel", sa.String(length=80), nullable=True),
    )
    op.add_column("content_items", sa.Column("publication_reference", sa.Text(), nullable=True))
    op.add_column("content_items", sa.Column("published_by_user_id", sa.Uuid(), nullable=True))
    op.add_column(
        "content_items",
        sa.Column("publication_idempotency_key", sa.String(length=200), nullable=True),
    )
    op.create_foreign_key(
        "fk_content_item_strategy",
        "content_items",
        "content_strategies",
        ["content_strategy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_content_item_strategy_version",
        "content_items",
        "strategy_versions",
        ["strategy_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_content_item_plan",
        "content_items",
        "content_plans",
        ["content_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_content_item_calendar_entry",
        "content_items",
        "calendar_entries",
        ["calendar_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_content_item_visual_preset",
        "content_items",
        "visual_presets",
        ["visual_preset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_content_item_published_by",
        "content_items",
        "users",
        ["published_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_content_item_calendar_entry",
        "content_items",
        ["calendar_entry_id"],
    )
    op.create_unique_constraint(
        "uq_content_publication_org_idempotency",
        "content_items",
        ["organization_id", "publication_idempotency_key"],
    )
    op.create_index(
        "ix_content_items_org_business_scheduled",
        "content_items",
        ["organization_id", "business_id", "scheduled_for"],
    )

    op.add_column("content_versions", sa.Column("service_id", sa.Uuid(), nullable=True))
    op.add_column(
        "content_versions",
        sa.Column("audience_segment_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "content_versions",
        sa.Column("marketing_objective_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "content_versions",
        sa.Column("notes", sa.Text(), server_default=sa.text("''"), nullable=False),
    )
    op.add_column(
        "content_versions",
        sa.Column("script", sa.Text(), server_default=sa.text("''"), nullable=False),
    )
    op.add_column(
        "content_versions",
        sa.Column("visual_prompt", sa.Text(), server_default=sa.text("''"), nullable=False),
    )
    op.add_column(
        "content_versions",
        sa.Column("negative_prompt", sa.Text(), server_default=sa.text("''"), nullable=False),
    )
    op.add_column(
        "content_versions",
        sa.Column(
            "brand_context_snapshot",
            sa.JSON(),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
    )
    op.add_column(
        "content_versions",
        sa.Column(
            "visual_preset_snapshot",
            sa.JSON(),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_content_version_service",
        "content_versions",
        "services",
        ["service_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_content_version_audience",
        "content_versions",
        "audience_segments",
        ["audience_segment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_content_version_objective",
        "content_versions",
        "marketing_objectives",
        ["marketing_objective_id"],
        ["id"],
        ondelete="SET NULL",
    )
    for column in (
        "notes",
        "script",
        "visual_prompt",
        "negative_prompt",
        "brand_context_snapshot",
        "visual_preset_snapshot",
    ):
        op.alter_column("content_versions", column, server_default=None)

    op.add_column(
        "approvals",
        sa.Column("component", sa.String(length=20), server_default="TEXT", nullable=False),
    )
    op.drop_constraint("uq_approval_version_stage", "approvals", type_="unique")
    op.execute(
        sa.text(
            """
            INSERT INTO approvals (
                id, organization_id, business_id, content_item_id, content_version_id,
                stage, component, status, requested_by_user_id, decided_by_user_id,
                decision_comment, decided_at, created_at, updated_at
            )
            SELECT
                gen_random_uuid(), organization_id, business_id, content_item_id,
                content_version_id, stage, 'IMAGE', status, requested_by_user_id,
                decided_by_user_id, decision_comment, decided_at, created_at, updated_at
            FROM approvals
            WHERE component = 'TEXT'
            """
        )
    )
    op.create_unique_constraint(
        "uq_approval_version_stage_component",
        "approvals",
        ["content_version_id", "stage", "component"],
    )
    op.alter_column("approvals", "component", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "uq_approval_version_stage_component",
        "approvals",
        type_="unique",
    )
    op.execute(sa.text("DELETE FROM approvals WHERE component = 'IMAGE'"))
    op.drop_column("approvals", "component")
    op.create_unique_constraint(
        "uq_approval_version_stage",
        "approvals",
        ["content_version_id", "stage"],
    )

    op.drop_constraint("fk_content_version_objective", "content_versions", type_="foreignkey")
    op.drop_constraint("fk_content_version_audience", "content_versions", type_="foreignkey")
    op.drop_constraint("fk_content_version_service", "content_versions", type_="foreignkey")
    for column in (
        "visual_preset_snapshot",
        "brand_context_snapshot",
        "negative_prompt",
        "visual_prompt",
        "script",
        "notes",
        "marketing_objective_id",
        "audience_segment_id",
        "service_id",
    ):
        op.drop_column("content_versions", column)

    op.drop_index("ix_content_items_org_business_scheduled", table_name="content_items")
    op.drop_constraint(
        "uq_content_publication_org_idempotency",
        "content_items",
        type_="unique",
    )
    op.drop_constraint("uq_content_item_calendar_entry", "content_items", type_="unique")
    op.drop_constraint("fk_content_item_published_by", "content_items", type_="foreignkey")
    op.drop_constraint("fk_content_item_visual_preset", "content_items", type_="foreignkey")
    op.drop_constraint("fk_content_item_calendar_entry", "content_items", type_="foreignkey")
    op.drop_constraint("fk_content_item_plan", "content_items", type_="foreignkey")
    op.drop_constraint("fk_content_item_strategy_version", "content_items", type_="foreignkey")
    op.drop_constraint("fk_content_item_strategy", "content_items", type_="foreignkey")
    for column in (
        "publication_idempotency_key",
        "published_by_user_id",
        "publication_reference",
        "publication_channel",
        "published_at",
        "scheduled_for",
        "visual_preset_id",
        "calendar_entry_id",
        "content_plan_id",
        "strategy_version_id",
        "content_strategy_id",
    ):
        op.drop_column("content_items", column)
