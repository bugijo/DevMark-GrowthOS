from fastapi.testclient import TestClient

from growthos.domain.enums import Role
from growthos.rate_limit import reset_login_rate_limiter
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


def test_cors_preflight_accepts_organization_context_header(client: TestClient) -> None:
    response = client.options(
        "/api/v1/organizations/current",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Organization-ID",
        },
    )
    assert response.status_code == 200
    allowed_headers = response.headers["Access-Control-Allow-Headers"].casefold()
    assert "x-organization-id" in allowed_headers


def test_login_rate_limit_blocks_normalized_key_and_reset_restores_success(
    client: TestClient,
) -> None:
    identity = create_identity(
        slug="rate-limit",
        email="rate-limit@example.com",
        role=Role.AGENCY_ADMIN,
    )
    for email in ("RATE-LIMIT@example.com", "rate-limit@example.com"):
        failed = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrong-password"},
        )
        assert failed.status_code == 401

    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0

    reset_login_rate_limiter()
    successful = client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert successful.status_code == 200


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
