"""Persiste custo informado por providers de IA sem inferir ausência.

Revision ID: 0016_ai_costs
Revises: 0015_ai_privacy
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_ai_costs"
down_revision: str | None = "0015_ai_privacy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_generations", sa.Column("cost_usd", sa.Numeric(18, 8), nullable=True))
    op.add_column(
        "ai_generations",
        sa.Column("cost_currency", sa.String(3), nullable=False, server_default="USD"),
    )
    op.add_column(
        "ai_generations",
        sa.Column("cost_status", sa.String(16), nullable=False, server_default="UNKNOWN"),
    )
    op.add_column("ai_generations", sa.Column("cost_origin", sa.String(48), nullable=True))
    op.add_column(
        "ai_generations", sa.Column("cost_accounted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        "ck_ai_generation_cost_status",
        "ai_generations",
        "cost_status IN ('CONFIRMED', 'ESTIMATED', 'UNKNOWN')",
    )
    op.add_column("ai_generation_attempts", sa.Column("cost_usd", sa.Numeric(18, 8), nullable=True))
    op.add_column(
        "ai_generation_attempts",
        sa.Column("cost_currency", sa.String(3), nullable=False, server_default="USD"),
    )
    op.add_column(
        "ai_generation_attempts",
        sa.Column("cost_status", sa.String(16), nullable=False, server_default="UNKNOWN"),
    )
    op.add_column("ai_generation_attempts", sa.Column("cost_origin", sa.String(48), nullable=True))
    op.create_check_constraint(
        "ck_ai_attempt_cost_status",
        "ai_generation_attempts",
        "cost_status IN ('CONFIRMED', 'ESTIMATED', 'UNKNOWN')",
    )
    op.add_column(
        "ai_usage_daily",
        sa.Column("confirmed_cost_usd", sa.Numeric(18, 8), nullable=False, server_default="0"),
    )
    op.add_column(
        "ai_usage_daily",
        sa.Column("estimated_cost_usd", sa.Numeric(18, 8), nullable=False, server_default="0"),
    )
    op.add_column(
        "ai_usage_daily",
        sa.Column("unknown_cost_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("ai_usage_daily", "unknown_cost_count")
    op.drop_column("ai_usage_daily", "estimated_cost_usd")
    op.drop_column("ai_usage_daily", "confirmed_cost_usd")
    op.drop_constraint("ck_ai_attempt_cost_status", "ai_generation_attempts", type_="check")
    op.drop_column("ai_generation_attempts", "cost_origin")
    op.drop_column("ai_generation_attempts", "cost_status")
    op.drop_column("ai_generation_attempts", "cost_currency")
    op.drop_column("ai_generation_attempts", "cost_usd")
    op.drop_constraint("ck_ai_generation_cost_status", "ai_generations", type_="check")
    op.drop_column("ai_generations", "cost_accounted_at")
    op.drop_column("ai_generations", "cost_origin")
    op.drop_column("ai_generations", "cost_status")
    op.drop_column("ai_generations", "cost_currency")
    op.drop_column("ai_generations", "cost_usd")
