"""Adiciona landing pages aprovadas por humanos e interessados por negócio cliente.

Revision ID: 0019_landing_leads
Revises: 0018_sales_leads
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_landing_leads"
down_revision: str | None = "0018_sales_leads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "landing_pages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("headline", sa.String(200), nullable=False),
        sa.Column("subheadline", sa.Text(), nullable=False),
        sa.Column("cta_label", sa.String(80), nullable=False),
        sa.Column("address", sa.String(300), nullable=False),
        sa.Column("contact_channel", sa.String(160), nullable=False),
        sa.Column("highlights", sa.JSON(), nullable=False),
        sa.Column("service_options", sa.JSON(), nullable=False),
        sa.Column("price_items", sa.JSON(), nullable=False),
        sa.Column("price_disclaimer", sa.Text(), nullable=False),
        sa.Column("demo_mode", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT','APPROVED')", name="ck_landing_page_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", name="uq_landing_page_business"),
        sa.UniqueConstraint("slug", name="uq_landing_page_slug"),
    )
    op.create_table(
        "business_leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("landing_page_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("service_requested", sa.String(120), nullable=False),
        sa.Column("price_item_label", sa.String(120), nullable=False),
        sa.Column("reference_price_cents", sa.Integer(), nullable=True),
        sa.Column("preferred_period", sa.String(120), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("next_action", sa.String(200), nullable=False),
        sa.Column("next_action_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source IN ('LANDING_DEMO','INSTAGRAM_POST','INSTAGRAM_STORY','INDICACAO',"
            "'WHATSAPP_DIRETO','OUTRO')",
            name="ck_business_lead_source",
        ),
        sa.CheckConstraint(
            "status IN ('NOVO','AGUARDANDO_DADOS','HORARIO_OFERTADO','CONFIRMADO','REALIZADO',"
            "'CANCELADO','NAO_COMPARECEU')",
            name="ck_business_lead_status",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["landing_page_id"], ["landing_pages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_business_leads_business_status",
        "business_leads",
        ["business_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_business_leads_business_status", table_name="business_leads")
    op.drop_table("business_leads")
    op.drop_table("landing_pages")
