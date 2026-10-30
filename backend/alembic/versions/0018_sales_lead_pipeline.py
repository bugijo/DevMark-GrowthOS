"""Adiciona pipeline local-first de pedidos comerciais DevMarkia.

Revision ID: 0018_sales_leads
Revises: 0017_ai_lifecycle
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018_sales_leads"
down_revision: str | None = "0017_ai_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sales_leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("service_classification", sa.String(32), nullable=False),
        sa.Column("classification_reason", sa.Text(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("company", sa.String(160), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("whatsapp", sa.String(24), nullable=False),
        sa.Column("business_type", sa.String(120), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("desired_timeline", sa.String(160), nullable=False),
        sa.Column("additional_info", sa.Text(), nullable=False),
        sa.Column("privacy_notice_version", sa.String(80), nullable=True),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proposal_draft", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "stage IN ('NEW_LEAD','CONTACT_PENDING','BRIEFING','PROPOSAL_PREPARATION',"
            "'PROPOSAL_SENT','NEGOTIATION','CONTRACTED','IN_PRODUCTION','DELIVERED','AFTER_SALES')",
            name="ck_sales_lead_stage",
        ),
        sa.CheckConstraint(
            "source IN ('PUBLIC_FORM','MANUAL','TEST')", name="ck_sales_lead_source"
        ),
        sa.CheckConstraint(
            "service_classification IN ('IN_SCOPE_LANDING_PAGE','OUT_OF_SCOPE','HUMAN_REVIEW')",
            name="ck_sales_lead_service_classification",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_sales_lead_org_idempotency"
        ),
    )
    op.create_index(
        "ix_sales_leads_org_stage_created",
        "sales_leads",
        ["organization_id", "stage", "created_at"],
    )
    op.create_table(
        "sales_lead_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["sales_leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sales_lead_tasks_org_due", "sales_lead_tasks", ["organization_id", "due_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_sales_lead_tasks_org_due", table_name="sales_lead_tasks")
    op.drop_table("sales_lead_tasks")
    op.drop_index("ix_sales_leads_org_stage_created", table_name="sales_leads")
    op.drop_table("sales_leads")
