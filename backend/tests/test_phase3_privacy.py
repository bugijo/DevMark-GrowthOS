from fastapi.testclient import TestClient
from sqlalchemy import func, select

from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import AuditLog, Membership, User
from tests.conftest import add_user_to_identity, create_identity, csrf_headers, login


def test_versioned_consent_history_and_export_are_scoped_to_current_tenant(
    client: TestClient,
) -> None:
    first = create_identity(
        slug="privacy-first", email="privacy-first@example.test", role=Role.AGENCY_ADMIN
    )
    second = create_identity(
        slug="privacy-second", email="privacy-second@example.test", role=Role.AGENCY_ADMIN
    )
    csrf = login(client, first)
    purposes = client.get("/api/v1/privacy/purposes")
    assert purposes.status_code == 200
    assert {item["code"] for item in purposes.json()} >= {"PLATFORM_OPERATION", "AUDIT_SECURITY"}
    for accepted, version in ((True, "v1.0"), (False, "v1.1")):
        response = client.post(
            "/api/v1/privacy/consents",
            headers=csrf_headers(csrf),
            json={"purpose_code": "COMMUNICATION", "policy_version": version, "accepted": accepted},
        )
        assert response.status_code == 201
    exported = client.get("/api/v1/privacy/export")
    assert exported.status_code == 200
    assert exported.json()["subject"]["email"] == first.email
    assert [item["policy_version"] for item in exported.json()["consents"]] == ["v1.1", "v1.0"]
    login(client, second)
    assert client.get("/api/v1/privacy/consents").json() == []
    assert first.email not in client.get("/api/v1/privacy/export").text


def test_deletion_request_is_administrative_anonymizes_subject_and_preserves_audit(
    client: TestClient,
) -> None:
    admin = create_identity(
        slug="privacy-admin",
        email="privacy-admin@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica",
    )
    subject = add_user_to_identity(
        admin, email="privacy-subject@example.test", role=Role.CLIENT_OWNER
    )
    subject_csrf = login(client, subject)
    created = client.post(
        "/api/v1/privacy/requests",
        headers=csrf_headers(subject_csrf),
        json={"request_type": "DELETION", "reason": "Encerrar meu acesso"},
    )
    assert created.status_code == 201
    with get_session_factory()() as session:
        audit_before = session.scalar(select(func.count()).select_from(AuditLog))
    admin_csrf = login(client, admin)
    pending = client.get("/api/v1/privacy/admin/requests")
    assert pending.status_code == 200
    resolved = client.post(
        f"/api/v1/privacy/admin/requests/{created.json()['id']}/resolve",
        headers=csrf_headers(admin_csrf),
        json={"decision": "COMPLETE", "notes": "Anonimização aprovada; logs legais preservados."},
    )
    assert resolved.status_code == 200, resolved.text
    with get_session_factory()() as session:
        user = session.get(User, subject.user_id)
        membership = session.get(Membership, subject.membership_id)
        assert user is not None and user.email.endswith("@redacted.invalid") and not user.is_active
        assert membership is not None and not membership.is_active
        assert session.scalar(select(func.count()).select_from(AuditLog)) > audit_before


def test_viewer_cannot_process_requests_or_change_retention(client: TestClient) -> None:
    viewer = create_identity(
        slug="privacy-viewer",
        email="privacy-viewer@example.test",
        role=Role.VIEWER,
        business_name="Cliente",
    )
    csrf = login(client, viewer)
    assert client.get("/api/v1/privacy/admin/requests").status_code == 403
    denied = client.put(
        "/api/v1/privacy/admin/retention/audit_logs",
        headers=csrf_headers(csrf),
        json={
            "retention_days": 2190,
            "legal_hold": True,
            "justification": "Obrigação legal e defesa de direitos.",
        },
    )
    assert denied.status_code == 403
