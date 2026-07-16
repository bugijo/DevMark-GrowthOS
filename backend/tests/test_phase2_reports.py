from datetime import UTC, datetime

from fastapi.testclient import TestClient

from growthos.database import get_session_factory
from growthos.domain.enums import (
    ApprovalComponent,
    ApprovalStage,
    ApprovalStatus,
    ContentStatus,
    Role,
)
from growthos.models import Approval, ContentItem, ContentVersion
from tests.conftest import Identity, create_identity, login


def _content_fixture(identity: Identity) -> None:
    organization_id = identity.organization_id
    business_id = identity.business_id
    user_id = identity.user_id
    assert business_id is not None
    with get_session_factory()() as session:
        item = ContentItem(
            organization_id=organization_id,
            business_id=business_id,
            status=ContentStatus.PUBLISHED,
            scheduled_for=datetime(2026, 7, 10, 12, tzinfo=UTC),
            published_at=datetime(2026, 7, 11, 12, tzinfo=UTC),
            publication_channel="Instagram",
            publication_reference="registro-manual-001",
            publication_idempotency_key="report-fixture-001",
            published_by_user_id=user_id,
            created_by_user_id=user_id,
        )
        session.add(item)
        session.flush()
        versions = []
        for version_number in (1, 2):
            version = ContentVersion(
                organization_id=organization_id,
                business_id=business_id,
                content_item_id=item.id,
                version_number=version_number,
                title=f"Conteúdo {version_number}",
                caption="Legenda",
                channel="Instagram",
                format="Feed",
                objective="Educar",
                provider_name="mock",
                created_by_user_id=user_id,
            )
            session.add(version)
            session.flush()
            versions.append(version)
        item.current_version_id = versions[-1].id
        session.add_all(
            [
                Approval(
                    organization_id=organization_id,
                    business_id=business_id,
                    content_item_id=item.id,
                    content_version_id=versions[-1].id,
                    stage=ApprovalStage.CLIENT,
                    component=ApprovalComponent.TEXT,
                    status=ApprovalStatus.APPROVED,
                    requested_by_user_id=user_id,
                    decided_by_user_id=user_id,
                    decided_at=datetime(2026, 7, 11, 10, tzinfo=UTC),
                ),
                Approval(
                    organization_id=organization_id,
                    business_id=business_id,
                    content_item_id=item.id,
                    content_version_id=versions[-1].id,
                    stage=ApprovalStage.CLIENT,
                    component=ApprovalComponent.IMAGE,
                    status=ApprovalStatus.CHANGES_REQUESTED,
                    requested_by_user_id=user_id,
                    decided_by_user_id=user_id,
                    decided_at=datetime(2026, 7, 11, 10, tzinfo=UTC),
                ),
            ]
        )
        session.commit()


def test_period_report_uses_real_scoped_data(client: TestClient) -> None:
    identity = create_identity(
        slug="report",
        email="report@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica Relatório",
    )
    assert identity.business_id is not None
    _content_fixture(identity)
    login(client, identity)

    response = client.get(
        f"/api/v1/businesses/{identity.business_id}/reports/period",
        params={"starts_on": "2026-07-01", "ends_on": "2026-07-31"},
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["content_total"] == 1
    assert report["content_by_status"]["PUBLISHED"] == 1
    assert report["content_versions_total"] == 2
    assert report["revisions_total"] == 1
    assert report["approvals_by_component"]["TEXT"]["APPROVED"] == 1
    assert report["approvals_by_component"]["IMAGE"]["CHANGES_REQUESTED"] == 1
    assert report["manual_publications_total"] == 1
    assert report["publications_by_channel"] == {"Instagram": 1}
    assert "impressoes" in report["unavailable_metrics"]


def test_period_report_rejects_cross_tenant_and_invalid_period(client: TestClient) -> None:
    first = create_identity(
        slug="report-first",
        email="report-first@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Primeiro cliente",
    )
    second = create_identity(
        slug="report-second",
        email="report-second@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Segundo cliente",
    )
    assert first.business_id is not None
    login(client, second)
    cross_tenant = client.get(
        f"/api/v1/businesses/{first.business_id}/reports/period",
        params={"starts_on": "2026-07-01", "ends_on": "2026-07-31"},
    )
    assert cross_tenant.status_code == 404

    login(client, first)
    invalid = client.get(
        f"/api/v1/businesses/{first.business_id}/reports/period",
        params={"starts_on": "2026-08-01", "ends_on": "2026-07-31"},
    )
    assert invalid.status_code == 422
