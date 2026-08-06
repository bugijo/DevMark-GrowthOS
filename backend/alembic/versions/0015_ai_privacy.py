"""Permite anonimização referencial dos dados de IA.

Revision ID: 0015_ai_privacy
Revises: 0014_ai_generations
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015_ai_privacy"
down_revision: str | None = "0014_ai_generations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ai_generations_requested_by_user_id_fkey", "ai_generations", type_="foreignkey"
    )
    op.alter_column("ai_generations", "requested_by_user_id", nullable=True)
    op.create_foreign_key(
        "ai_generations_requested_by_user_id_fkey",
        "ai_generations",
        "users",
        ["requested_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "ai_generation_feedback_user_id_fkey", "ai_generation_feedback", type_="foreignkey"
    )
    op.alter_column("ai_generation_feedback", "user_id", nullable=True)
    op.create_foreign_key(
        "ai_generation_feedback_user_id_fkey",
        "ai_generation_feedback",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    connection = op.get_bind()
    null_generation = connection.execute(
        sa.text("SELECT 1 FROM ai_generations WHERE requested_by_user_id IS NULL LIMIT 1")
    ).first()
    null_feedback = connection.execute(
        sa.text("SELECT 1 FROM ai_generation_feedback WHERE user_id IS NULL LIMIT 1")
    ).first()
    if null_generation or null_feedback:
        raise RuntimeError(
            "Downgrade bloqueado: existem referências de IA anonimizadas; restaure os vínculos "
            "somente com base legal antes de voltar à 0014."
        )
    op.drop_constraint(
        "ai_generation_feedback_user_id_fkey", "ai_generation_feedback", type_="foreignkey"
    )
    op.alter_column("ai_generation_feedback", "user_id", nullable=False)
    op.create_foreign_key(
        "ai_generation_feedback_user_id_fkey",
        "ai_generation_feedback",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "ai_generations_requested_by_user_id_fkey", "ai_generations", type_="foreignkey"
    )
    op.alter_column("ai_generations", "requested_by_user_id", nullable=False)
    op.create_foreign_key(
        "ai_generations_requested_by_user_id_fkey",
        "ai_generations",
        "users",
        ["requested_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
