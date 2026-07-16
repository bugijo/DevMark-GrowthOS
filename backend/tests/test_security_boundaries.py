from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import Membership, Notification, Organization, User
from growthos.security import hash_password
from tests.conftest import create_identity, csrf_headers, login


def _create_business(client: TestClient, headers: dict[str, str], name: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/businesses",
        json={"name": name, "segment": "Veterinária"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_reviewer(
    client: TestClient,
    headers: dict[str, str],
    business_id: str,
    suffix: str,
) -> dict[str, str]:
    credentials = {
        "email": f"reviewer-{suffix}@example.com",
        "password": "reviewer-password-123",
    }
    response = client.post(
        f"/api/v1/businesses/{business_id}/reviewers",
        json={"name": f"Reviewer {suffix}", **credentials},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return credentials


def _prepare_client_review(
    client: TestClient,
    headers: dict[str, str],
    business_id: str,
    suffix: str,
) -> dict[str, Any]:
    brand = client.put(
        f"/api/v1/businesses/{business_id}/brand-profile",
        json={"brand_name": f"Brand {suffix}", "internal_notes": "Somente agência"},
        headers=headers,
    )
    assert brand.status_code == 200, brand.text
    content = client.post(
        "/api/v1/contents/generate",
        json={
            "business_id": business_id,
            "objective": f"Conteúdo {suffix}",
            "channel": "INSTAGRAM",
            "format": "FEED",
        },
        headers=headers,
    )
    assert content.status_code == 201, content.text
    payload = content.json()
    assert (
        client.post(
            f"/api/v1/contents/{payload['id']}/submit-internal",
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/contents/{payload['id']}/send-to-client",
            headers=headers,
        ).status_code
        == 200
    )
    return payload


@pytest.mark.parametrize("role", [Role.CLIENT_OWNER, Role.CLIENT_REVIEWER, Role.VIEWER])
def test_database_rejects_active_client_membership_without_business(role: Role) -> None:
    with get_session_factory()() as session:
        organization = Organization(name=f"Invalid {role.value}", slug=f"invalid-{role.value}")
        user = User(
            email=f"invalid-{role.value.casefold()}@example.com",
            name="Invalid scope",
            password_hash=hash_password("test-password-123"),
        )
        session.add_all([organization, user])
        session.flush()
        session.add(
            Membership(
                organization_id=organization.id,
                user_id=user.id,
                role=role,
                business_id=None,
                is_active=True,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


@pytest.mark.parametrize("role", [Role.CLIENT_OWNER, Role.CLIENT_REVIEWER])
def test_client_decision_roles_read_only_their_business_audit_log(
    client: TestClient,
    role: Role,
) -> None:
    identity = create_identity(
        slug=f"audit-{role.value.casefold()}",
        email=f"audit-{role.value.casefold()}@example.com",
        role=role,
        business_name=f"Audit {role.value}",
    )
    login(client, identity)
    response = client.get("/api/v1/audit-logs")
    assert response.status_code == 200, response.text
    assert all(item["business_id"] == str(identity.business_id) for item in response.json())


def test_viewer_cannot_read_audit_or_mark_notification_read(client: TestClient) -> None:
    viewer = create_identity(
        slug="audit-viewer",
        email="audit-viewer@example.com",
        role=Role.VIEWER,
        business_name="Audit Viewer",
    )
    with get_session_factory()() as session:
        notification = Notification(
            organization_id=viewer.organization_id,
            business_id=viewer.business_id,
            recipient_user_id=viewer.user_id,
            type="VIEWER_NOTICE",
            title="Somente leitura",
            message="A pessoa pode consultar, mas não alterar o estado.",
        )
        session.add(notification)
        session.commit()
        notification_id = notification.id
    csrf = login(client, viewer)
    assert client.get("/api/v1/audit-logs").status_code == 403
    assert client.get("/api/v1/notifications").status_code == 200
    assert (
        client.post(
            f"/api/v1/notifications/{notification_id}/read",
            headers=csrf_headers(csrf),
        ).status_code
        == 403
    )


def test_business_scope_isolated_inside_same_organization(client: TestClient) -> None:
    admin = create_identity(
        slug="same-organization",
        email="same-organization-admin@example.com",
        role=Role.AGENCY_ADMIN,
    )
    admin_headers = csrf_headers(login(client, admin))
    business_a = _create_business(client, admin_headers, "Business A")
    business_b = _create_business(client, admin_headers, "Business B")
    reviewer_a = _create_reviewer(client, admin_headers, business_a["id"], "business-a")
    reviewer_b = _create_reviewer(client, admin_headers, business_b["id"], "business-b")
    content_a = _prepare_client_review(client, admin_headers, business_a["id"], "A")
    content_b = _prepare_client_review(client, admin_headers, business_b["id"], "B")

    # Mesmo um registro interno incoerente não pode atravessar o escopo da empresa.
    with get_session_factory()() as session:
        reviewer_a_user = session.scalar(select(User).where(User.email == reviewer_a["email"]))
        assert reviewer_a_user is not None
        cross_notification = Notification(
            organization_id=admin.organization_id,
            business_id=UUID(business_b["id"]),
            recipient_user_id=reviewer_a_user.id,
            type="CROSS_SCOPE_TEST",
            title="Não deve aparecer",
            message="Registro propositalmente incoerente para testar falha fechada.",
            resource_type="content_item",
            resource_id=UUID(content_b["id"]),
        )
        session.add(cross_notification)
        session.commit()
        cross_notification_id = cross_notification.id

    portal_a = TestClient(client.app)
    csrf_a = portal_a.post("/api/v1/auth/login", json=reviewer_a).json()["csrf_token"]
    listed_businesses = portal_a.get("/api/v1/businesses")
    assert {item["id"] for item in listed_businesses.json()} == {business_a["id"]}
    assert portal_a.get(f"/api/v1/businesses/{business_a['id']}").status_code == 200
    assert portal_a.get(f"/api/v1/businesses/{business_b['id']}").status_code == 404
    assert portal_a.get(f"/api/v1/businesses/{business_b['id']}/brand-profile").status_code == 404
    assert {item["id"] for item in portal_a.get("/api/v1/contents").json()} == {content_a["id"]}
    assert portal_a.get(f"/api/v1/contents/{content_b['id']}").status_code == 404
    assert (
        portal_a.post(
            f"/api/v1/contents/{content_b['id']}/approve",
            json={},
            headers=csrf_headers(csrf_a),
        ).status_code
        == 404
    )
    assert (
        portal_a.post(
            f"/api/v1/contents/{content_b['id']}/request-changes",
            json={"comment": "Tentativa cruzada"},
            headers=csrf_headers(csrf_a),
        ).status_code
        == 404
    )
    notifications_a = portal_a.get("/api/v1/notifications").json()
    assert {item["resource_id"] for item in notifications_a} == {content_a["id"]}
    assert (
        portal_a.post(
            f"/api/v1/notifications/{cross_notification_id}/read",
            headers=csrf_headers(csrf_a),
        ).status_code
        == 404
    )
    audit_a = portal_a.get("/api/v1/audit-logs")
    assert audit_a.status_code == 200, audit_a.text
    assert all(item["business_id"] == business_a["id"] for item in audit_a.json())

    portal_b = TestClient(client.app)
    login_b = portal_b.post("/api/v1/auth/login", json=reviewer_b)
    assert login_b.status_code == 200
    notification_b = portal_b.get("/api/v1/notifications").json()[0]
    assert (
        portal_a.post(
            f"/api/v1/notifications/{notification_b['id']}/read",
            headers=csrf_headers(csrf_a),
        ).status_code
        == 404
    )


def test_archiving_business_revokes_portal_and_hides_content(client: TestClient) -> None:
    admin = create_identity(
        slug="archive-scope",
        email="archive-admin@example.com",
        role=Role.AGENCY_ADMIN,
    )
    admin_headers = csrf_headers(login(client, admin))
    business = _create_business(client, admin_headers, "Archived Business")
    reviewer = _create_reviewer(client, admin_headers, business["id"], "archive")
    content = _prepare_client_review(client, admin_headers, business["id"], "Archive")

    portal = TestClient(client.app)
    login_response = portal.post("/api/v1/auth/login", json=reviewer)
    assert login_response.status_code == 200
    assert portal.get(f"/api/v1/contents/{content['id']}").status_code == 200

    archived = client.delete(
        f"/api/v1/businesses/{business['id']}",
        headers=admin_headers,
    )
    assert archived.status_code == 204
    assert client.get(f"/api/v1/contents/{content['id']}").status_code == 404
    assert all(item["id"] != content["id"] for item in client.get("/api/v1/contents").json())
    assert portal.get("/api/v1/auth/me").status_code == 401
    assert portal.get("/api/v1/contents").status_code == 401
    assert portal.get("/api/v1/notifications").status_code == 401
