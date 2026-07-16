"""Adiciona catálogos, presets visuais e biblioteca de mídia.

Revision ID: 0005_catalogs_media
Revises: 0004_secure_identity
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_catalogs_media"
down_revision: str | None = "0004_secure_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _tenant_business_columns() -> list[sa.Column]:
    return [
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
    ]


def _tenant_business_foreign_keys() -> list[sa.ForeignKeyConstraint]:
    return [
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
    ]


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_tenant_business_columns(),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        *_tenant_business_foreign_keys(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "business_id",
            "name",
            name="uq_service_org_business_name",
        ),
    )
    op.create_index(
        "ix_services_org_business_active",
        "services",
        ["organization_id", "business_id", "is_active"],
    )

    op.create_table(
        "audience_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_tenant_business_columns(),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("needs", sa.JSON(), nullable=False),
        sa.Column("objections", sa.JSON(), nullable=False),
        sa.Column("location", sa.String(length=240), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        *_tenant_business_foreign_keys(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "business_id",
            "name",
            name="uq_audience_segment_org_business_name",
        ),
    )
    op.create_index(
        "ix_audience_segments_org_business_active",
        "audience_segments",
        ["organization_id", "business_id", "is_active"],
    )

    op.create_table(
        "marketing_objectives",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_tenant_business_columns(),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("planned_indicators", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        *_tenant_business_foreign_keys(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "business_id",
            "name",
            name="uq_marketing_objective_org_business_name",
        ),
    )
    op.create_index(
        "ix_marketing_objectives_org_business_active",
        "marketing_objectives",
        ["organization_id", "business_id", "is_active"],
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_tenant_business_columns(),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("storage_provider", sa.String(length=40), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("display_name", sa.String(length=240), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("origin", sa.String(length=40), nullable=False),
        sa.Column("processing_status", sa.String(length=40), nullable=False),
        sa.Column("metadata_safe", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        *_tenant_business_foreign_keys(),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("byte_size >= 0", name="ck_media_asset_byte_size_non_negative"),
        sa.CheckConstraint(
            "processing_status IN ('PENDING', 'READY', 'REJECTED', 'FAILED', 'ARCHIVED')",
            name="ck_media_asset_processing_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "object_key", name="uq_media_asset_org_object_key"),
    )
    op.create_index(
        "ix_media_assets_org_business_created",
        "media_assets",
        ["organization_id", "business_id", "created_at"],
    )

    op.create_table(
        "visual_presets",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_tenant_business_columns(),
        sa.Column("brand_profile_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("format", sa.String(length=80), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=20), nullable=False),
        sa.Column("creation_mode", sa.String(length=20), nullable=False),
        sa.Column("color_palette", sa.JSON(), nullable=False),
        sa.Column("fonts", sa.JSON(), nullable=False),
        sa.Column("logo_media_asset_id", sa.Uuid(), nullable=True),
        sa.Column("logo_position", sa.String(length=80), nullable=False),
        sa.Column("logo_scale_percent", sa.Integer(), nullable=True),
        sa.Column("safe_margins", sa.JSON(), nullable=False),
        sa.Column("background_style", sa.Text(), nullable=False),
        sa.Column("photographic_style", sa.Text(), nullable=False),
        sa.Column("realism_level", sa.String(length=80), nullable=False),
        sa.Column("lighting", sa.Text(), nullable=False),
        sa.Column("composition", sa.Text(), nullable=False),
        sa.Column("max_text_characters", sa.Integer(), nullable=True),
        sa.Column("text_rules", sa.JSON(), nullable=False),
        sa.Column("base_prompt", sa.Text(), nullable=False),
        sa.Column("negative_prompt", sa.Text(), nullable=False),
        sa.Column("allowed_elements", sa.JSON(), nullable=False),
        sa.Column("forbidden_elements", sa.JSON(), nullable=False),
        sa.Column("visual_signature", sa.Text(), nullable=False),
        sa.Column("default_cta", sa.String(length=300), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        *_tenant_business_foreign_keys(),
        sa.ForeignKeyConstraint(["brand_profile_id"], ["brand_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["logo_media_asset_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "creation_mode IN ('TEMPLATE', 'AI_IMAGE', 'HYBRID', 'MANUAL')",
            name="ck_visual_preset_creation_mode",
        ),
        sa.CheckConstraint("version > 0", name="ck_visual_preset_version_positive"),
        sa.CheckConstraint(
            "logo_scale_percent IS NULL OR (logo_scale_percent >= 1 AND logo_scale_percent <= 100)",
            name="ck_visual_preset_logo_scale_percent",
        ),
        sa.CheckConstraint(
            "max_text_characters IS NULL OR max_text_characters >= 0",
            name="ck_visual_preset_max_text_characters",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "business_id",
            "name",
            name="uq_visual_preset_org_business_name",
        ),
    )
    op.create_index(
        "ix_visual_presets_org_business_active",
        "visual_presets",
        ["organization_id", "business_id", "is_active"],
    )

    op.create_table(
        "content_version_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_tenant_business_columns(),
        sa.Column("content_version_id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        *_tenant_business_foreign_keys(),
        sa.ForeignKeyConstraint(
            ["content_version_id"], ["content_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "role IN ('PRIMARY', 'REFERENCE', 'BACKGROUND', 'OUTPUT')",
            name="ck_content_version_media_role",
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_content_version_media_sort_order"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_version_id",
            "media_asset_id",
            "role",
            name="uq_content_version_media_role",
        ),
    )
    op.create_index(
        "ix_content_version_media_org_business",
        "content_version_media",
        ["organization_id", "business_id"],
    )


def downgrade() -> None:
    op.drop_table("content_version_media")
    op.drop_table("visual_presets")
    op.drop_table("media_assets")
    op.drop_table("marketing_objectives")
    op.drop_table("audience_segments")
    op.drop_table("services")
