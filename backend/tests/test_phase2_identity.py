from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from growthos.config import get_settings
from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import Job, Membership, PasswordResetToken, User
from growthos.services.tokens import TokenPurpose, derive_token
from tests.conftest import add_user_to_identity, create_identity, csrf_headers, login


def test_secure_invitation_is_single_use_and_job_contains_no_token(client: TestClient) -> None:
    admin = create_identity(
        slug="secure-invite",
        email="invite-admin@example.com",
        role=Role.AGENCY_ADMIN,
    )
    headers = csrf_headers(login(client, admin))
    created = client.post(
        "/api/v1/members/invitations",
        json={
            "name": "Nova Estrategista",
            "email": "strategist@example.com",
            "role": "STRATEGIST",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    invite = created.json()
    assert invite["status"] == "PENDING"
    token = derive_token(
        get_settings().effective_token_secret_key,
        TokenPurpose.ORGANIZATION_INVITE,
        UUID(invite["id"]),
    )

    inspected = client.post(
        "/api/v1/auth/invitations/inspect",
        json={"token": token},
    )
    assert inspected.status_code == 200, inspected.text
    assert inspected.json()["masked_email"] == "s***@example.com"
    assert inspected.json()["requires_account_setup"] is True

    accepted = client.post(
        "/api/v1/auth/invitations/accept",
        json={
            "token": token,
            "name": "Nova Estrategista",
            "password": "new-strategist-password",
        },
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["membership"]["role"] == "STRATEGIST"
    assert (
        client.post(
            "/api/v1/auth/invitations/accept",
            json={
                "token": token,
                "name": "Nova Estrategista",
                "password": "new-strategist-password",
            },
        ).status_code
        == 400
    )

    invited_client = TestClient(client.app)
    assert (
        invited_client.post(
            "/api/v1/auth/login",
            json={"email": "strategist@example.com", "password": "new-strategist-password"},
        ).status_code
        == 200
    )

    with get_session_factory()() as session:
        job = session.scalar(select(Job).where(Job.type == "identity.invite.email"))
        assert job is not None
        assert job.payload == {"invite_id": invite["id"]}
        assert token not in str(job.payload)

    actions = {entry["action"] for entry in client.get("/api/v1/audit-logs").json()}
    assert {"invitation.created", "invitation.accepted"} <= actions


def test_client_owner_can_invite_only_reviewers_for_own_business(client: TestClient) -> None:
    owner = create_identity(
        slug="client-owner-invite",
        email="owner@example.com",
        role=Role.CLIENT_OWNER,
        business_name="Empresa do owner",
    )
    headers = csrf_headers(login(client, owner))
    allowed = client.post(
        "/api/v1/members/invitations",
        json={
            "name": "Revisora",
            "email": "reviewer-owner@example.com",
            "role": "CLIENT_REVIEWER",
            "business_id": str(owner.business_id),
        },
        headers=headers,
    )
    assert allowed.status_code == 201, allowed.text
    forbidden = client.post(
        "/api/v1/members/invitations",
        json={
            "name": "Estrategista",
            "email": "strategist-owner@example.com",
            "role": "STRATEGIST",
        },
        headers=headers,
    )
    assert forbidden.status_code == 403


def test_password_reset_is_generic_single_use_and_revokes_old_session(
    client: TestClient,
) -> None:
    admin = create_identity(
        slug="password-reset",
        email="reset@example.com",
        role=Role.AGENCY_ADMIN,
        password="old-password-123",
    )
    login(client, admin)
    requested = client.post(
        "/api/v1/auth/password-recovery",
        json={"email": admin.email},
    )
    unknown = client.post(
        "/api/v1/auth/password-recovery",
        json={"email": "unknown-reset@example.com"},
    )
    assert requested.status_code == unknown.status_code == 202
    assert requested.json() == unknown.json()

    with get_session_factory()() as session:
        reset = session.scalar(
            select(PasswordResetToken).where(PasswordResetToken.user_id == admin.user_id)
        )
        assert reset is not None
        reset_id = reset.id
        job = session.scalar(select(Job).where(Job.type == "identity.password_reset.email"))
        assert job is not None
        assert job.payload == {"reset_id": str(reset_id)}
    token = derive_token(
        get_settings().effective_token_secret_key,
        TokenPurpose.PASSWORD_RESET,
        reset_id,
    )
    changed = client.post(
        "/api/v1/auth/password-reset",
        json={"token": token, "new_password": "new-password-secure-123"},
    )
    assert changed.status_code == 200, changed.text
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/password-reset",
            json={"token": token, "new_password": "another-password-123"},
        ).status_code
        == 400
    )

    fresh_client = TestClient(client.app)
    assert (
        fresh_client.post(
            "/api/v1/auth/login",
            json={"email": admin.email, "password": "old-password-123"},
        ).status_code
        == 401
    )
    assert (
        fresh_client.post(
            "/api/v1/auth/login",
            json={"email": admin.email, "password": "new-password-secure-123"},
        ).status_code
        == 200
    )


def test_agency_admin_manages_roles_but_not_own_access(client: TestClient) -> None:
    admin = create_identity(
        slug="member-management",
        email="members-admin@example.com",
        role=Role.AGENCY_ADMIN,
    )
    strategist = add_user_to_identity(
        admin,
        email="managed-strategist@example.com",
        role=Role.STRATEGIST,
    )
    headers = csrf_headers(login(client, admin))
    listed = client.get("/api/v1/members")
    assert listed.status_code == 200
    assert {item["user"]["email"] for item in listed.json()} == {
        admin.email,
        strategist.email,
    }
    updated = client.patch(
        f"/api/v1/members/{strategist.membership_id}",
        json={"role": "CONTENT_EDITOR"},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["role"] == "CONTENT_EDITOR"

    managed_client = TestClient(client.app)
    assert login(managed_client, strategist)
    suspended = client.patch(
        f"/api/v1/members/{strategist.membership_id}",
        json={"status": "SUSPENDED"},
        headers=headers,
    )
    assert suspended.status_code == 200, suspended.text
    assert managed_client.get("/api/v1/auth/me").status_code == 401
    reactivated = client.patch(
        f"/api/v1/members/{strategist.membership_id}",
        json={"status": "ACTIVE"},
        headers=headers,
    )
    assert reactivated.status_code == 200, reactivated.text
    assert managed_client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.patch(
            f"/api/v1/members/{admin.membership_id}",
            json={"status": "SUSPENDED"},
            headers=headers,
        ).status_code
        == 409
    )

    with get_session_factory()() as session:
        membership = session.get(Membership, strategist.membership_id)
        user = session.get(User, strategist.user_id)
        assert membership is not None and membership.role == Role.CONTENT_EDITOR
        assert user is not None and user.is_active is True
        assert user.session_version == 4
