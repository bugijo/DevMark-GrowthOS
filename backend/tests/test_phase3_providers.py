from fastapi.testclient import TestClient

from growthos.domain.enums import Role
from tests.conftest import create_identity, csrf_headers, login


def test_provider_catalog_keeps_mock_available_and_never_returns_secret_values(
    client: TestClient, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    admin = create_identity(
        slug="providers-admin", email="providers-admin@example.test", role=Role.AGENCY_ADMIN
    )
    csrf = login(client, admin)
    catalog = client.get("/api/v1/providers")
    assert catalog.status_code == 200
    assert any(item["provider"] == "MOCK" and item["is_active"] for item in catalog.json())

    monkeypatch.setenv("FUTURE_PROVIDER_TOKEN", "secret-value-must-never-leave-server")
    updated = client.put(
        "/api/v1/providers/TEXT/EXTERNAL_FUTURE",
        headers=csrf_headers(csrf),
        json={
            "is_active": True,
            "priority": 50,
            "fallback_provider": "MOCK",
            "timeout_seconds": 5,
            "max_attempts": 2,
            "test_mode": True,
            "secret_environment_key": "FUTURE_PROVIDER_TOKEN",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["configured_by_environment"] is True
    assert "secret-value" not in updated.text
    assert updated.json()["secret_environment_key"] == "FUTURE_PROVIDER_TOKEN"


def test_optional_providers_require_explicit_mock_fallback_and_hermes_is_optional(
    client: TestClient, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    admin = create_identity(
        slug="providers-hermes", email="providers-hermes@example.test", role=Role.AGENCY_ADMIN
    )
    csrf = login(client, admin)
    invalid = client.put(
        "/api/v1/providers/TEXT/HERMES",
        headers=csrf_headers(csrf),
        json={
            "is_active": True,
            "priority": 10,
            "fallback_provider": None,
            "timeout_seconds": 2,
            "max_attempts": 1,
            "test_mode": True,
            "secret_environment_key": None,
        },
    )
    assert invalid.status_code == 422
    monkeypatch.delenv("HERMES_BASE_URL", raising=False)
    tested = client.post("/api/v1/providers/TEXT/HERMES/test", headers=csrf_headers(csrf))
    assert tested.status_code == 200
    assert tested.json()["status"] == "DISABLED"
    assert "fallback mock" in tested.json()["message"].casefold()


def test_provider_configuration_is_tenant_scoped_and_management_is_denied_to_viewer(
    client: TestClient,
) -> None:
    first = create_identity(
        slug="providers-first", email="providers-first@example.test", role=Role.AGENCY_ADMIN
    )
    second = create_identity(
        slug="providers-second", email="providers-second@example.test", role=Role.AGENCY_ADMIN
    )
    viewer = create_identity(
        slug="providers-viewer",
        email="providers-viewer@example.test",
        role=Role.VIEWER,
        business_name="Cliente viewer",
    )
    first_csrf = login(client, first)
    response = client.put(
        "/api/v1/providers/IMAGE/EXTERNAL_FUTURE",
        headers=csrf_headers(first_csrf),
        json={
            "is_active": True,
            "priority": 33,
            "fallback_provider": "MOCK",
            "timeout_seconds": 8,
            "max_attempts": 2,
            "test_mode": True,
            "secret_environment_key": "IMAGE_PROVIDER_TOKEN",
        },
    )
    assert response.status_code == 200
    login(client, second)
    second_catalog = client.get("/api/v1/providers")
    external = next(
        item
        for item in second_catalog.json()
        if item["kind"] == "IMAGE" and item["provider"] == "EXTERNAL_FUTURE"
    )
    assert external["id"] is None
    assert external["priority"] == 100

    viewer_csrf = login(client, viewer)
    denied = client.put(
        "/api/v1/providers/TEXT/MOCK",
        headers=csrf_headers(viewer_csrf),
        json={
            "is_active": True,
            "priority": 0,
            "fallback_provider": None,
            "timeout_seconds": 5,
            "max_attempts": 1,
            "test_mode": True,
            "secret_environment_key": None,
        },
    )
    assert denied.status_code == 403
