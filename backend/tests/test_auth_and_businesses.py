from fastapi.testclient import TestClient

from growthos.domain.enums import Role
from tests.conftest import create_identity, csrf_headers, login


def test_health_login_csrf_and_logout(client: TestClient) -> None:
    admin = create_identity(slug="auth", email="admin-auth@example.com", role=Role.AGENCY_ADMIN)
    assert client.get("/api/v1/health").json() == {
        "status": "ok",
        "database": "ok",
        "provider": "mock",
    }
    csrf = login(client, admin)
    assert client.get("/api/v1/auth/me").status_code == 200

    blocked = client.post("/api/v1/businesses", json={"name": "Sem CSRF", "segment": "Pet"})
    assert blocked.status_code == 403

    created = client.post(
        "/api/v1/businesses",
        json={"name": "Clínica Feliz", "segment": "Veterinária"},
        headers=csrf_headers(csrf),
    )
    assert created.status_code == 201
    assert created.json()["organization_id"] == str(admin.organization_id)

    assert client.post("/api/v1/auth/logout", headers=csrf_headers(csrf)).status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_create_reviewer_hashes_password_and_rejects_duplicate_email(client: TestClient) -> None:
    admin = create_identity(
        slug="reviewer",
        email="admin-reviewer@example.com",
        role=Role.AGENCY_ADMIN,
    )
    csrf = login(client, admin)
    business = client.post(
        "/api/v1/businesses",
        json={"name": "Pet Review", "segment": "Pet shop"},
        headers=csrf_headers(csrf),
    ).json()
    payload = {
        "name": "Cliente Revisor",
        "email": "reviewer-created@example.com",
        "password": "reviewer-password-123",
    }
    created = client.post(
        f"/api/v1/businesses/{business['id']}/reviewers",
        json=payload,
        headers=csrf_headers(csrf),
    )
    assert created.status_code == 201, created.text
    assert created.json()["membership"]["business_id"] == business["id"]
    assert created.json()["membership"]["role"] == "CLIENT_REVIEWER"
    assert "password" not in created.text
    assert "hash" not in created.text

    duplicate = client.post(
        f"/api/v1/businesses/{business['id']}/reviewers",
        json=payload,
        headers=csrf_headers(csrf),
    )
    assert duplicate.status_code == 409

    reviewer_client = TestClient(client.app)
    logged = reviewer_client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert logged.status_code == 200
    assert logged.json()["membership"]["business_id"] == business["id"]


def test_viewer_can_read_but_cannot_write(client: TestClient) -> None:
    viewer = create_identity(
        slug="viewer",
        email="viewer@example.com",
        role=Role.VIEWER,
        business_name="Visible Business",
    )
    csrf = login(client, viewer)
    assert client.get(f"/api/v1/businesses/{viewer.business_id}").status_code == 200
    forbidden = client.post(
        "/api/v1/businesses",
        json={"name": "Forbidden", "segment": "Pet"},
        headers=csrf_headers(csrf),
    )
    assert forbidden.status_code == 403
