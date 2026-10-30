from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import AIGeneration
from tests.conftest import create_identity, csrf_headers, login


def test_ai_generation_uses_offline_mock_and_records_history(client: TestClient) -> None:
    admin = create_identity(
        slug="ai-offline",
        email="ai-offline@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica isolada",
    )
    assert admin.business_id is not None
    csrf = login(client, admin)
    generated = client.post(
        f"/api/v1/businesses/{admin.business_id}/ai/generations",
        headers=csrf_headers(csrf),
        json={
            "task": "CONTENT_IDEAS",
            "instruction": "Use um tom acolhedor",
            "alternatives": 3,
        },
    )
    assert generated.status_code == 201, generated.text
    body = generated.json()
    assert body["provider"] == "mock"
    assert body["simulated"] is True
    assert body["requires_approval"] is True
    assert body["can_publish_automatically"] is False
    assert len(body["alternatives"]) == 3

    with get_session_factory()() as session:
        stored = session.scalar(select(AIGeneration).where(AIGeneration.id == UUID(body["id"])))
        assert stored is not None
        assert set(stored.context_snapshot) == {
            "brand",
            "services",
            "audiences",
            "objectives",
            "planning",
        }
        serialized_context = str(stored.context_snapshot).casefold()
        assert "password" not in serialized_context
        assert "token" not in serialized_context
        assert "cookie" not in serialized_context
        assert "internal_notes" not in serialized_context
        assert "signed_url" not in serialized_context

    history = client.get(f"/api/v1/businesses/{admin.business_id}/ai/generations")
    assert history.status_code == 200
    assert history.json()[0]["id"] == body["id"]


def test_ai_generation_is_tenant_scoped_and_viewer_cannot_generate(client: TestClient) -> None:
    first = create_identity(
        slug="ai-first",
        email="ai-first@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente A",
    )
    second = create_identity(
        slug="ai-second",
        email="ai-second@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente B",
    )
    assert first.business_id is not None and second.business_id is not None
    csrf = login(client, first)
    generated = client.post(
        f"/api/v1/businesses/{first.business_id}/ai/generations",
        headers=csrf_headers(csrf),
        json={"task": "TITLE", "alternatives": 1},
    )
    generation_id = generated.json()["id"]

    login(client, second)
    assert client.get(f"/api/v1/ai/generations/{generation_id}").status_code == 404
    assert client.get(f"/api/v1/businesses/{first.business_id}/ai/generations").status_code == 404

    viewer = create_identity(
        slug="ai-viewer",
        email="ai-viewer@example.test",
        role=Role.VIEWER,
        business_name="Cliente viewer",
    )
    assert viewer.business_id is not None
    viewer_csrf = login(client, viewer)
    denied = client.post(
        f"/api/v1/businesses/{viewer.business_id}/ai/generations",
        headers=csrf_headers(viewer_csrf),
        json={"task": "TITLE", "alternatives": 1},
    )
    assert denied.status_code == 403


def test_ai_rejects_invalid_alternative_count(client: TestClient) -> None:
    admin = create_identity(
        slug="ai-invalid",
        email="ai-invalid@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente",
    )
    assert admin.business_id is not None
    csrf = login(client, admin)
    response = client.post(
        f"/api/v1/businesses/{admin.business_id}/ai/generations",
        headers=csrf_headers(csrf),
        json={"task": "TITLE", "alternatives": 2},
    )
    assert response.status_code == 422
