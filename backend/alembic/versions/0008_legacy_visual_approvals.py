"""Normaliza aprovações visuais legadas sem mídia.

Revision ID: 0008_legacy_visual_approvals
Revises: 0007_content_editorial
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_legacy_visual_approvals"
down_revision: str | None = "0007_content_editorial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LEGACY_IMAGE_MATCH = """
    image.component = 'IMAGE'
    AND image.status <> 'CANCELLED'
    AND NOT EXISTS (
        SELECT 1
        FROM content_version_media
        WHERE content_version_media.content_version_id = image.content_version_id
          AND content_version_media.organization_id = image.organization_id
          AND content_version_media.business_id = image.business_id
          AND content_version_media.role IN ('PRIMARY', 'OUTPUT')
    )
    AND EXISTS (
        SELECT 1
        FROM approvals AS text_approval
        WHERE text_approval.content_version_id = image.content_version_id
          AND text_approval.stage = image.stage
          AND text_approval.component = 'TEXT'
          AND text_approval.requested_by_user_id = image.requested_by_user_id
          AND text_approval.status = image.status
          AND text_approval.created_at = image.created_at
          AND text_approval.updated_at = image.updated_at
          AND text_approval.decided_by_user_id IS NOT DISTINCT FROM image.decided_by_user_id
          AND text_approval.decision_comment IS NOT DISTINCT FROM image.decision_comment
          AND text_approval.decided_at IS NOT DISTINCT FROM image.decided_at
    )
"""


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            INSERT INTO audit_logs (
                id, organization_id, business_id, actor_user_id, action,
                resource_type, resource_id, metadata, created_at
            )
            SELECT
                gen_random_uuid(), image.organization_id, image.business_id, NULL,
                'content.migration_visual_review_required', 'content_item',
                image.content_item_id,
                json_build_object(
                    'migration', '0008_legacy_visual_approvals',
                    'content_status_from', content_items.status,
                    'content_status_to', CASE
                        WHEN content_items.status IN ('CLIENT_REVIEW', 'APPROVED', 'SCHEDULED')
                            THEN 'CHANGES_REQUESTED'
                        ELSE content_items.status
                    END,
                    'image_status_from', image.status,
                    'image_status_to', 'CANCELLED',
                    'reason', 'legacy_approval_without_visual_media'
                ),
                now()
            FROM approvals AS image
            JOIN content_items ON content_items.id = image.content_item_id
            WHERE {_LEGACY_IMAGE_MATCH}
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE content_items
            SET status = 'CHANGES_REQUESTED', updated_at = now()
            WHERE content_items.status IN ('CLIENT_REVIEW', 'APPROVED', 'SCHEDULED')
              AND EXISTS (
                  SELECT 1
                  FROM approvals AS image
                  WHERE image.content_item_id = content_items.id
                    AND image.content_version_id = content_items.current_version_id
                    AND {_LEGACY_IMAGE_MATCH}
              )
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE approvals AS image
            SET status = 'CANCELLED',
                decided_by_user_id = NULL,
                decision_comment = NULL,
                decided_at = NULL,
                updated_at = now()
            WHERE {_LEGACY_IMAGE_MATCH}
            """
        )
    )


def downgrade() -> None:
    # A normalização remove estados que seriam inválidos na Fase 2. Restaurá-los
    # reintroduziria aprovações visuais sem mídia, portanto o downgrade é intencionalmente no-op.
    pass
