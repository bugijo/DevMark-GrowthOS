"""Completa idempotência, cancelamento e aplicação de alternativas de IA.

Revision ID: 0017_ai_lifecycle
Revises: 0016_ai_costs
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017_ai_lifecycle"
down_revision: str | None = "0016_ai_costs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_generations", sa.Column("idempotency_key", sa.String(200), nullable=True))
    op.add_column("ai_generations", sa.Column("request_fingerprint", sa.String(64), nullable=True))
    op.add_column(
        "ai_generations", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("ai_generations", sa.Column("cancelled_by_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_ai_generation_cancelled_by",
        "ai_generations",
        "users",
        ["cancelled_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_ai_generation_org_idempotency", "ai_generations", ["organization_id", "idempotency_key"]
    )
    op.add_column(
        "ai_generation_alternatives", sa.Column("applied_content_item_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "ai_generation_alternatives",
        sa.Column("applied_content_version_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "ai_generation_alternatives", sa.Column("applied_by_user_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "ai_generation_alternatives",
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_ai_alternative_content",
        "ai_generation_alternatives",
        "content_items",
        ["applied_content_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_ai_alternative_version",
        "ai_generation_alternatives",
        "content_versions",
        ["applied_content_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_ai_alternative_applied_by",
        "ai_generation_alternatives",
        "users",
        ["applied_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_ai_alternative_applied_by", "ai_generation_alternatives", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ai_alternative_version", "ai_generation_alternatives", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ai_alternative_content", "ai_generation_alternatives", type_="foreignkey"
    )
    op.drop_column("ai_generation_alternatives", "applied_at")
    op.drop_column("ai_generation_alternatives", "applied_by_user_id")
    op.drop_column("ai_generation_alternatives", "applied_content_version_id")
    op.drop_column("ai_generation_alternatives", "applied_content_item_id")
    op.drop_constraint("uq_ai_generation_org_idempotency", "ai_generations", type_="unique")
    op.drop_constraint("fk_ai_generation_cancelled_by", "ai_generations", type_="foreignkey")
    op.drop_column("ai_generations", "cancelled_by_user_id")
    op.drop_column("ai_generations", "cancelled_at")
    op.drop_column("ai_generations", "request_fingerprint")
    op.drop_column("ai_generations", "idempotency_key")
