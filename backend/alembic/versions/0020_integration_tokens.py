"""Adiciona credenciais de integração somente leitura (ex.: Hermes).

Revision ID: 0020_integration_tokens
Revises: 0019_landing_leads
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020_integration_tokens"
down_revision: str | None = "0019_landing_leads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_integration_tokens_organization_id", "integration_tokens", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_integration_tokens_organization_id", table_name="integration_tokens")
    op.drop_table("integration_tokens")
