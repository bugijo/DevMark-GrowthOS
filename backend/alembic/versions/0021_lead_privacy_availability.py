"""Adiciona aviso de privacidade por estabelecimento, horários e campos de pedido real.

Somente aditiva: as colunas de contato nascem vazias e a restrição de origem é
ampliada (nenhum valor existente deixa de ser aceito).

Revision ID: 0021_lead_privacy
Revises: 0020_integration_tokens
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021_lead_privacy"
down_revision: str | None = "0020_integration_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_SOURCES = (
    "source IN ('LANDING_DEMO','INSTAGRAM_POST','INSTAGRAM_STORY','INDICACAO',"
    "'WHATSAPP_DIRETO','OUTRO')"
)
_NEW_SOURCES = (
    "source IN ('LANDING_DEMO','LANDING_PAGE','INSTAGRAM_POST','INSTAGRAM_STORY',"
    "'INDICACAO','WHATSAPP_DIRETO','OUTRO')"
)


def upgrade() -> None:
    op.create_table(
        "lead_privacy_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("controller_name", sa.String(200), nullable=False),
        sa.Column("privacy_contact", sa.String(200), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("legal_basis", sa.String(32), nullable=False),
        sa.Column("data_categories", sa.JSON(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("notice_text", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT','APPROVED')", name="ck_lead_privacy_status"),
        sa.CheckConstraint(
            "legal_basis IN ('CONSENTIMENTO','PROCEDIMENTOS_PRELIMINARES','LEGITIMO_INTERESSE')",
            name="ck_lead_privacy_legal_basis",
        ),
        sa.CheckConstraint("retention_days BETWEEN 1 AND 730", name="ck_lead_privacy_retention"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", name="uq_lead_privacy_business"),
    )
    op.create_table(
        "business_availability",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("slots", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("confirmed_by_business", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", name="uq_business_availability_business"),
    )
    with op.batch_alter_table("business_leads") as batch:
        batch.add_column(sa.Column("contact_name", sa.String(120), nullable=True))
        batch.add_column(sa.Column("contact_phone", sa.String(32), nullable=True))
        batch.add_column(sa.Column("privacy_notice_version", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("consent_recorded_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True))
        batch.drop_constraint("ck_business_lead_source", type_="check")
        batch.create_check_constraint("ck_business_lead_source", _NEW_SOURCES)


def downgrade() -> None:
    with op.batch_alter_table("business_leads") as batch:
        batch.drop_constraint("ck_business_lead_source", type_="check")
        batch.create_check_constraint("ck_business_lead_source", _OLD_SOURCES)
        batch.drop_column("anonymized_at")
        batch.drop_column("consent_recorded_at")
        batch.drop_column("privacy_notice_version")
        batch.drop_column("contact_phone")
        batch.drop_column("contact_name")
    op.drop_table("business_availability")
    op.drop_table("lead_privacy_settings")
