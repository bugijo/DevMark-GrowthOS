"""Impede rodadas de aprovação duplicadas para a mesma versão.

Revision ID: 0002_unique_approval
Revises: 0001_initial
Create Date: 2026-07-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_unique_approval"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_approval_version_stage",
        "approvals",
        ["content_version_id", "stage"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_approval_version_stage",
        "approvals",
        type_="unique",
    )
