from fastapi.testclient import TestClient

from growthos.database import get_session_factory
from growthos.domain.enums import ContentStatus, Role
from growthos.models import ContentItem, ContentVersion
from tests.conftest import Identity, create_identity, login


def _add_contents(identity: Identity, count: int) -> list[str]:
    assert identity.business_id is not None
    content_ids: list[str] = []
    with get_session_factory()() as session:
        for index in range(count):
            content = ContentItem(
                organization_id=identity.organization_id,
                business_id=identity.business_id,
                status=ContentStatus.DRAFT,
                created_by_user_id=identity.user_id,
            )
            session.add(content)
            session.flush()
            version = ContentVersion(
                organization_id=identity.organization_id,
                business_id=identity.business_id,
                content_item_id=content.id,
                version_number=1,
                title=f"Conteúdo {index}",
                caption="Fixture de paginação.",
                channel="INSTAGRAM",
                format="FEED",
                objective="Validar paginação com tenant.",
                provider_name="mock",
                created_by_user_id=identity.user_id,
            )
            session.add(version)
            session.flush()
            content.current_version_id = version.id
            content_ids.append(str(content.id))
        session.commit()
    return content_ids


def test_content_pagination_is_stable_and_tenant_scoped(client: TestClient) -> None:
    owner = create_identity(
        slug="page-owner",
        email="page-owner@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica paginação",
    )
    outsider = create_identity(
        slug="page-outsider",
        email="page-outsider@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica externa",
    )
    expected = set(_add_contents(owner, 3))
    outsider_ids = set(_add_contents(outsider, 2))
    login(client, owner)

    first = client.get("/api/v1/contents", params={"limit": 2, "offset": 0})
    second = client.get("/api/v1/contents", params={"limit": 2, "offset": 2})

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    first_ids = {item["id"] for item in first.json()}
    second_ids = {item["id"] for item in second.json()}
    assert len(first_ids) == 2
    assert len(second_ids) == 1
    assert first_ids.isdisjoint(second_ids)
    assert first_ids | second_ids == expected
    assert (first_ids | second_ids).isdisjoint(outsider_ids)


def test_content_pagination_rejects_unbounded_parameters(client: TestClient) -> None:
    identity = create_identity(
        slug="page-limits",
        email="page-limits@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica limites",
    )
    login(client, identity)

    assert client.get("/api/v1/contents", params={"limit": 101}).status_code == 422
    assert client.get("/api/v1/contents", params={"offset": -1}).status_code == 422
