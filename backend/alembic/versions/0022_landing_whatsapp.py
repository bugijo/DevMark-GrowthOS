"""Adiciona o WhatsApp da landing e a contagem diária agregada de cliques.

Somente aditiva: a coluna nasce vazia (botão escondido) e a tabela de métricas
não guarda nenhum dado pessoal.

Revision ID: 0022_landing_whatsapp
Revises: 0021_lead_privacy
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022_landing_whatsapp"
down_revision: str | None = "0021_lead_privacy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "landing_pages",
        sa.Column("whatsapp_number", sa.String(20), nullable=False, server_default=""),
    )
    op.create_table(
        "landing_daily_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("landing_page_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("event", sa.String(32), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("event IN ('whatsapp_click')", name="ck_landing_metric_event"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["landing_page_id"], ["landing_pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("landing_page_id", "day", "event", name="uq_landing_metric_day_event"),
    )


def downgrade() -> None:
    op.drop_table("landing_daily_metrics")
    op.drop_column("landing_pages", "whatsapp_number")
