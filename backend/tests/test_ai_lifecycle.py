from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from growthos.database import get_session_factory
from growthos.domain.enums import ContentStatus, Role
from growthos.models import AIGeneration, AIGenerationAlternative, AuditLog, ContentItem
from tests.conftest import create_identity, csrf_headers, login


def _generate(client: TestClient, business_id: UUID, csrf: str, key: str) -> dict[str, object]:
    response = client.post(
        f"/api/v1/businesses/{business_id}/ai/generations",
        headers=csrf_headers(csrf),
        json={"task": "CONTENT_IDEAS", "alternatives": 1, "idempotency_key": key},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_generation_idempotency_replays_same_resource_and_rejects_changed_input(
    client: TestClient,
) -> None:
    admin = create_identity(
        slug="ai-idempotent",
        email="ai-idempotent@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica idempotente",
    )
    assert admin.business_id is not None
    csrf = login(client, admin)
    key = "qa006-generation-key"
    first = _generate(client, admin.business_id, csrf, key)
    replay = _generate(client, admin.business_id, csrf, key)
    assert replay["id"] == first["id"]

    conflict = client.post(
        f"/api/v1/businesses/{admin.business_id}/ai/generations",
        headers=csrf_headers(csrf),
        json={"task": "TITLE", "alternatives": 1, "idempotency_key": key},
    )
    assert conflict.status_code == 409
    with get_session_factory()() as session:
        assert session.scalar(select(func.count(AIGeneration.id))) == 1

    regeneration_headers = {
        **csrf_headers(csrf),
        "Idempotency-Key": "qa006-regeneration-key",
    }
    regenerated = client.post(
        f"/api/v1/ai/generations/{first['id']}/regenerate",
        headers=regeneration_headers,
    )
    regeneration_replay = client.post(
        f"/api/v1/ai/generations/{first['id']}/regenerate",
        headers=regeneration_headers,
    )
    assert regenerated.status_code == regeneration_replay.status_code == 201
    assert regenerated.json()["id"] == regeneration_replay.json()["id"]


def test_generation_idempotency_is_scoped_by_tenant(client: TestClient) -> None:
    first = create_identity(
        slug="ai-key-first",
        email="ai-key-first@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente A",
    )
    second = create_identity(
        slug="ai-key-second",
        email="ai-key-second@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente B",
    )
    assert first.business_id and second.business_id
    key = "qa006-shared-tenant-key"
    first_id = _generate(client, first.business_id, login(client, first), key)["id"]
    second_id = _generate(client, second.business_id, login(client, second), key)["id"]
    assert first_id != second_id


def test_cancel_is_authorized_tenant_scoped_idempotent_and_audited(client: TestClient) -> None:
    admin = create_identity(
        slug="ai-cancel",
        email="ai-cancel@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente cancelamento",
    )
    other = create_identity(
        slug="ai-cancel-other",
        email="ai-cancel-other@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Outro tenant",
    )
    viewer = create_identity(
        slug="ai-cancel-viewer",
        email="ai-cancel-viewer@example.test",
        role=Role.VIEWER,
        business_name="Viewer",
    )
    assert admin.business_id and other.business_id and viewer.business_id
    csrf = login(client, admin)
    generation = _generate(client, admin.business_id, csrf, "qa006-cancel-key")
    generation_id = str(generation["id"])

    login(client, other)
    assert (
        client.post(
            f"/api/v1/ai/generations/{generation_id}/cancel",
            headers=csrf_headers(client.cookies["growthos_csrf"]),
        ).status_code
        == 404
    )
    login(client, viewer)
    assert (
        client.post(
            f"/api/v1/ai/generations/{generation_id}/cancel",
            headers=csrf_headers(client.cookies["growthos_csrf"]),
        ).status_code
        == 403
    )
    csrf = login(client, admin)
    first = client.post(
        f"/api/v1/ai/generations/{generation_id}/cancel", headers=csrf_headers(csrf)
    )
    replay = client.post(
        f"/api/v1/ai/generations/{generation_id}/cancel", headers=csrf_headers(csrf)
    )
    assert first.status_code == replay.status_code == 200
    assert first.json()["status"] == "CANCELLED"
    assert replay.json()["cancelled_at"] == first.json()["cancelled_at"]
    missing = client.post(f"/api/v1/ai/generations/{uuid4()}/cancel", headers=csrf_headers(csrf))
    assert missing.status_code == 404
    with get_session_factory()() as session:
        logs = session.scalars(
            select(AuditLog).where(AuditLog.action == "ai.generation_cancelled")
        ).all()
        assert len(logs) == 1
        assert "qa006-cancel-key" not in str(logs[0].details)


def test_apply_alternative_creates_one_draft_version_without_approval_or_publication(
    client: TestClient,
) -> None:
    admin = create_identity(
        slug="ai-apply",
        email="ai-apply@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica aplicação",
    )
    assert admin.business_id
    csrf = login(client, admin)
    generation = _generate(client, admin.business_id, csrf, "qa006-apply-key")
    alternative_id = str(generation["alternatives"][0]["id"])
    path = f"/api/v1/ai/generations/{generation['id']}/alternatives/{alternative_id}/apply"
    payload = {"channel": "INSTAGRAM", "format": "FEED", "objective": "Educação preventiva"}
    first = client.post(path, headers=csrf_headers(csrf), json=payload)
    replay = client.post(path, headers=csrf_headers(csrf), json=payload)
    assert first.status_code == replay.status_code == 201
    assert replay.json()["id"] == first.json()["id"]
    assert first.json()["status"] == ContentStatus.DRAFT
    assert first.json()["approvals"] == []
    assert first.json()["published_at"] is None
    assert first.json()["current_version"]["provider_name"] == "ai:mock"
    with get_session_factory()() as session:
        assert session.scalar(select(func.count(ContentItem.id))) == 1
        alternative = session.get(AIGenerationAlternative, UUID(alternative_id))
        assert alternative is not None
        assert alternative.applied_content_version_id == UUID(first.json()["current_version"]["id"])
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(AuditLog.action == "ai.alternative_applied")
            )
            == 1
        )

    assert (
        client.post(
            f"/api/v1/ai/generations/{generation['id']}/cancel", headers=csrf_headers(csrf)
        ).status_code
        == 409
    )


def test_apply_rejects_cancelled_missing_other_tenant_and_user_without_permission(
    client: TestClient,
) -> None:
    admin = create_identity(
        slug="ai-apply-negative",
        email="ai-apply-negative@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente aplicação negativa",
    )
    other = create_identity(
        slug="ai-apply-negative-other",
        email="ai-apply-negative-other@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Outro tenant",
    )
    viewer = create_identity(
        slug="ai-apply-negative-viewer",
        email="ai-apply-negative-viewer@example.test",
        role=Role.VIEWER,
        business_name="Viewer",
    )
    assert admin.business_id and other.business_id and viewer.business_id
    csrf = login(client, admin)
    generation = _generate(client, admin.business_id, csrf, "qa006-negative-key")
    generation_id = str(generation["id"])
    alternative_id = str(generation["alternatives"][0]["id"])
    apply_path = f"/api/v1/ai/generations/{generation_id}/alternatives/{alternative_id}/apply"
    assert (
        client.post(
            f"/api/v1/ai/generations/{generation_id}/cancel", headers=csrf_headers(csrf)
        ).status_code
        == 200
    )
    assert client.post(apply_path, headers=csrf_headers(csrf), json={}).status_code == 409

    login(client, other)
    assert (
        client.post(
            apply_path, headers=csrf_headers(client.cookies["growthos_csrf"]), json={}
        ).status_code
        == 404
    )
    login(client, viewer)
    assert (
        client.post(
            apply_path, headers=csrf_headers(client.cookies["growthos_csrf"]), json={}
        ).status_code
        == 403
    )
    csrf = login(client, admin)
    assert (
        client.post(
            f"/api/v1/ai/generations/{uuid4()}/alternatives/{uuid4()}/apply",
            headers=csrf_headers(csrf),
            json={},
        ).status_code
        == 404
    )


def test_concurrent_replay_contract_has_database_uniqueness(client: TestClient) -> None:
    admin = create_identity(
        slug="ai-concurrent",
        email="ai-concurrent@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente concorrente",
    )
    assert admin.business_id
    csrf = login(client, admin)
    key = "qa006-concurrent-key"

    def request() -> tuple[int, str]:
        response = client.post(
            f"/api/v1/businesses/{admin.business_id}/ai/generations",
            headers=csrf_headers(csrf),
            json={"task": "TITLE", "alternatives": 1, "idempotency_key": key},
        )
        return response.status_code, str(response.json().get("id"))

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: request(), range(2)))
    assert {status for status, _ in results} == {201}
    assert len({generation_id for _, generation_id in results}) == 1
