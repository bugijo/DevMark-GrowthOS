from fastapi.testclient import TestClient
from sqlalchemy import select

from growthos.config import Settings, get_settings
from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import Membership
from growthos.rate_limit import InMemoryLoginRateLimiter, reset_login_rate_limiter
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


def test_session_and_csrf_cookies_use_expected_security_attributes(client: TestClient) -> None:
    identity = create_identity(
        slug="cookie-attributes",
        email="cookie-attributes@example.com",
        role=Role.AGENCY_ADMIN,
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200
    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(value for value in cookies if value.startswith("growthos_session="))
    csrf_cookie = next(value for value in cookies if value.startswith("growthos_csrf="))
    assert "HttpOnly" in session_cookie
    assert "SameSite=lax" in session_cookie
    assert "Secure" not in session_cookie
    assert "HttpOnly" not in csrf_cookie
    assert "SameSite=lax" in csrf_cookie


def test_production_login_marks_both_cookies_secure(client: TestClient) -> None:
    identity = create_identity(
        slug="secure-cookie",
        email="secure-cookie@example.com",
        role=Role.AGENCY_ADMIN,
    )
    settings = Settings(
        _env_file=None,
        app_env="production",
        auth_secret_key="g8B!2zQ#9mK$4vN@7xR%3cT&6pL*1sD_5wF+0hJ",
        session_cookie_secure=True,
        session_cookie_same_site="strict",
        allowed_origins="https://growthos.example.com",
        ai_provider="mock",
        seed_demo_data=False,
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": identity.email, "password": identity.password},
        )
    finally:
        client.app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 200
    cookies = response.headers.get_list("set-cookie")
    assert all("Secure" in value for value in cookies)
    assert all("SameSite=strict" in value for value in cookies)


def test_csrf_rejects_header_or_cookie_that_does_not_match_session(client: TestClient) -> None:
    identity = create_identity(
        slug="csrf-mismatch",
        email="csrf-mismatch@example.com",
        role=Role.AGENCY_ADMIN,
    )
    csrf = login(client, identity)
    wrong_header = client.post(
        "/api/v1/businesses",
        json={"name": "CSRF errado", "segment": "Pet"},
        headers={"X-CSRF-Token": "wrong-token"},
    )
    assert wrong_header.status_code == 403

    client.cookies.set("growthos_csrf", "wrong-cookie")
    wrong_cookie = client.post(
        "/api/v1/businesses",
        json={"name": "Cookie errado", "segment": "Pet"},
        headers=csrf_headers(csrf),
    )
    assert wrong_cookie.status_code == 403


def test_session_revalidates_membership_revocation(client: TestClient) -> None:
    identity = create_identity(
        slug="revoked-membership",
        email="revoked-membership@example.com",
        role=Role.AGENCY_ADMIN,
    )
    login(client, identity)
    with get_session_factory()() as session:
        membership = session.scalar(
            select(Membership).where(Membership.id == identity.membership_id)
        )
        assert membership is not None
        membership.is_active = False
        session.commit()

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


def test_login_rate_limit_blocks_email_rotation_from_same_origin(client: TestClient) -> None:
    identity = create_identity(
        slug="rate-origin",
        email="valid-rate-origin@example.com",
        role=Role.AGENCY_ADMIN,
    )
    for attempt in range(4):
        failed = client.post(
            "/api/v1/auth/login",
            json={"email": f"rotated-{attempt}@example.com", "password": "wrong-password"},
        )
        assert failed.status_code == 401

    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert blocked.status_code == 429


def test_login_rate_limit_tracks_identity_across_origins(client: TestClient) -> None:
    identity = create_identity(
        slug="rate-identity",
        email="rate-identity@example.com",
        role=Role.AGENCY_ADMIN,
    )
    first_origin = TestClient(client.app, client=("198.51.100.10", 51000))
    second_origin = TestClient(client.app, client=("198.51.100.11", 51001))
    for origin in (first_origin, second_origin):
        failed = origin.post(
            "/api/v1/auth/login",
            json={"email": identity.email, "password": "wrong-password"},
        )
        assert failed.status_code == 401

    blocked = first_origin.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert blocked.status_code == 429


def test_in_memory_rate_limiter_has_bounded_storage() -> None:
    limiter = InMemoryLoginRateLimiter(clock=lambda: 0.0, max_entries=2)
    for key in ("one", "two", "three"):
        limiter.register_failure(key, window_seconds=60)

    assert limiter.tracked_entry_count == 2
    assert limiter.retry_after("one", attempts=1, window_seconds=60) is None


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
    assert payload["email"] not in duplicate.text

    reviewer_client = TestClient(client.app)
    logged = reviewer_client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert logged.status_code == 200
    assert logged.json()["membership"]["business_id"] == business["id"]


def test_direct_reviewer_provisioning_is_blocked_in_production(client: TestClient) -> None:
    identity = create_identity(
        slug="production-reviewer",
        email="production-reviewer-admin@example.com",
        role=Role.AGENCY_ADMIN,
    )
    settings = Settings(
        _env_file=None,
        app_env="production",
        auth_secret_key="g8B!2zQ#9mK$4vN@7xR%3cT&6pL*1sD_5wF+0hJ",
        session_cookie_secure=True,
        allowed_origins="https://growthos.example.com",
        ai_provider="mock",
        seed_demo_data=False,
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    production_client = TestClient(client.app, base_url="https://testserver")
    try:
        login_response = production_client.post(
            "/api/v1/auth/login",
            json={"email": identity.email, "password": identity.password},
        )
        assert login_response.status_code == 200
        csrf = login_response.json()["csrf_token"]
        business = production_client.post(
            "/api/v1/businesses",
            json={"name": "Production Business", "segment": "Pet"},
            headers=csrf_headers(csrf),
        )
        assert business.status_code == 201
        blocked = production_client.post(
            f"/api/v1/businesses/{business.json()['id']}/reviewers",
            json={
                "name": "Blocked Reviewer",
                "email": "blocked-reviewer@example.com",
                "password": "blocked-reviewer-password",
            },
            headers=csrf_headers(csrf),
        )
    finally:
        production_client.close()
        client.app.dependency_overrides.pop(get_settings, None)

    assert blocked.status_code == 403


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
