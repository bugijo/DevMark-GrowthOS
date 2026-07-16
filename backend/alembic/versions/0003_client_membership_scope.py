"""Exige empresa para memberships ativas do portal cliente.

Revision ID: 0003_client_scope
Revises: 0002_unique_approval
Create Date: 2026-07-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_client_scope"
down_revision: str | None = "0002_unique_approval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Dados antigos inconsistentes ficam revogados; a migração não tenta adivinhar
    # a qual empresa uma pessoa deveria ter acesso.
    op.execute(
        """
        UPDATE memberships
        SET is_active = false
        WHERE is_active = true
          AND business_id IS NULL
          AND role IN ('CLIENT_OWNER', 'CLIENT_REVIEWER', 'VIEWER')
        """
    )
    op.create_check_constraint(
        "ck_membership_active_client_business",
        "memberships",
        """
        is_active = false
        OR role NOT IN ('CLIENT_OWNER', 'CLIENT_REVIEWER', 'VIEWER')
        OR business_id IS NOT NULL
        """,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_membership_active_client_business",
        "memberships",
        type_="check",
    )
