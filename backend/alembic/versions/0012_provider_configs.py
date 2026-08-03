"""Adiciona configuração segura e organizacional de providers.

Revision ID: 0012_provider_configs
Revises: 0011_sensitive_review
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_provider_configs"
down_revision: str | None = "0011_sensitive_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("fallback_provider", sa.String(length=32), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("test_mode", sa.Boolean(), nullable=False),
        sa.Column("secret_environment_key", sa.String(length=120), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=32), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("priority >= 0", name="ck_provider_config_priority"),
        sa.CheckConstraint("timeout_seconds BETWEEN 1 AND 120", name="ck_provider_config_timeout"),
        sa.CheckConstraint("max_attempts BETWEEN 1 AND 10", name="ck_provider_config_attempts"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "kind", "provider", name="uq_provider_config_org_kind_provider"
        ),
    )
    op.create_index(
        "ix_provider_configs_org_kind_priority",
        "provider_configs",
        ["organization_id", "kind", "priority"],
    )


def downgrade() -> None:
    op.drop_index("ix_provider_configs_org_kind_priority", table_name="provider_configs")
    op.drop_table("provider_configs")
