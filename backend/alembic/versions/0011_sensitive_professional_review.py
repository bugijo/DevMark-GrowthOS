"""Adiciona classificação sensível e revisão profissional por versão.

Revision ID: 0011_sensitive_review
Revises: 0010_phase3_notifications
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_sensitive_review"
down_revision: str | None = "0010_phase3_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "memberships",
        sa.Column(
            "professional_review_granted",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_membership_tenant_user_identity",
        "memberships",
        ["id", "organization_id", "user_id"],
    )
    op.alter_column("memberships", "professional_review_granted", server_default=None)

    op.add_column(
        "content_versions",
        sa.Column("is_sensitive", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "content_versions",
        sa.Column(
            "sensitivity_categories",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )
    op.add_column(
        "content_versions",
        sa.Column(
            "sensitivity_codes",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )
    op.add_column(
        "content_versions",
        sa.Column("sensitivity_score", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "content_versions",
        sa.Column(
            "sensitivity_provider",
            sa.String(length=80),
            server_default="legacy_unassessed",
            nullable=False,
        ),
    )
    op.add_column(
        "content_versions",
        sa.Column(
            "sensitivity_provider_version",
            sa.String(length=80),
            server_default="legacy-v1",
            nullable=False,
        ),
    )
    op.add_column(
        "content_versions",
        sa.Column(
            "sensitivity_assessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_content_version_sensitivity_score",
        "content_versions",
        "sensitivity_score >= 0 AND sensitivity_score <= 100",
    )
    op.create_unique_constraint(
        "uq_content_version_tenant_identity",
        "content_versions",
        ["id", "organization_id", "business_id", "content_item_id"],
    )
    for column in (
        "is_sensitive",
        "sensitivity_categories",
        "sensitivity_codes",
        "sensitivity_score",
        "sensitivity_provider",
        "sensitivity_provider_version",
        "sensitivity_assessed_at",
    ):
        op.alter_column("content_versions", column, server_default=None)

    op.create_table(
        "professional_content_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("content_item_id", sa.Uuid(), nullable=False),
        sa.Column("content_version_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_membership_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('APPROVED', 'CHANGES_REQUESTED')",
            name="ck_professional_review_decision",
        ),
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
            ["reviewer_membership_id", "organization_id", "reviewer_user_id"],
            ["memberships.id", "memberships.organization_id", "memberships.user_id"],
            name="fk_professional_review_membership_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "content_version_id",
            name="uq_professional_review_version",
        ),
    )
    op.create_index(
        "ix_professional_review_content_created",
        "professional_content_reviews",
        ["organization_id", "business_id", "content_item_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_professional_review_content_created",
        table_name="professional_content_reviews",
    )
    op.drop_table("professional_content_reviews")

    op.drop_constraint(
        "uq_content_version_tenant_identity",
        "content_versions",
        type_="unique",
    )
    op.drop_constraint(
        "ck_content_version_sensitivity_score",
        "content_versions",
        type_="check",
    )
    for column in (
        "sensitivity_assessed_at",
        "sensitivity_provider_version",
        "sensitivity_provider",
        "sensitivity_score",
        "sensitivity_codes",
        "sensitivity_categories",
        "is_sensitive",
    ):
        op.drop_column("content_versions", column)

    op.drop_constraint(
        "uq_membership_tenant_user_identity",
        "memberships",
        type_="unique",
    )
    op.drop_column("memberships", "professional_review_granted")
