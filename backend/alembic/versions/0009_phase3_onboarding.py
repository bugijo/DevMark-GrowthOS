"""Adiciona o onboarding consolidado e completa o perfil de marca.

Revision ID: 0009_phase3_onboarding
Revises: 0008_legacy_visual_approvals
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_phase3_onboarding"
down_revision: str | None = "0008_legacy_visual_approvals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_BRAND_JSON_COLUMNS = (
    "secondary_colors",
    "fonts",
    "logo_media_asset_ids",
    "visual_reference_media_asset_ids",
    "allowed_rules",
    "forbidden_rules",
    "required_terms",
    "legal_rules",
    "image_restrictions",
)


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="America/Sao_Paulo",
            nullable=False,
        ),
    )
    op.add_column(
        "businesses",
        sa.Column(
            "onboarding_status",
            sa.String(length=24),
            server_default="NOT_STARTED",
            nullable=False,
        ),
    )
    op.add_column(
        "businesses",
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_business_onboarding_status",
        "businesses",
        "onboarding_status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED')",
    )

    for column_name in _BRAND_JSON_COLUMNS:
        op.add_column(
            "brand_profiles",
            sa.Column(
                column_name,
                sa.JSON(),
                server_default=sa.text("'[]'::json"),
                nullable=False,
            ),
        )
    op.add_column(
        "brand_profiles",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_check_constraint(
        "ck_brand_profile_version_positive",
        "brand_profiles",
        "version > 0",
    )

    op.create_table(
        "business_onboardings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False),
        sa.Column("completed_steps", sa.JSON(), nullable=False),
        sa.Column("step_data", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("started_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("completed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["started_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('IN_PROGRESS', 'COMPLETED')",
            name="ck_business_onboarding_record_status",
        ),
        sa.CheckConstraint(
            "current_step >= 1 AND current_step <= 15",
            name="ck_business_onboarding_current_step",
        ),
        sa.CheckConstraint("revision > 0", name="ck_business_onboarding_revision_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "business_id",
            name="uq_business_onboarding_org_business",
        ),
    )
    op.create_index(
        "ix_business_onboardings_org_status",
        "business_onboardings",
        ["organization_id", "status"],
    )

    op.alter_column("businesses", "timezone", server_default=None)
    op.alter_column("businesses", "onboarding_status", server_default=None)
    for column_name in _BRAND_JSON_COLUMNS:
        op.alter_column("brand_profiles", column_name, server_default=None)
    op.alter_column("brand_profiles", "version", server_default=None)


def downgrade() -> None:
    op.drop_table("business_onboardings")
    op.drop_constraint(
        "ck_brand_profile_version_positive",
        "brand_profiles",
        type_="check",
    )
    op.drop_column("brand_profiles", "version")
    for column_name in reversed(_BRAND_JSON_COLUMNS):
        op.drop_column("brand_profiles", column_name)
    op.drop_constraint(
        "ck_business_onboarding_status",
        "businesses",
        type_="check",
    )
    op.drop_column("businesses", "onboarding_completed_at")
    op.drop_column("businesses", "onboarding_status")
    op.drop_column("businesses", "timezone")
