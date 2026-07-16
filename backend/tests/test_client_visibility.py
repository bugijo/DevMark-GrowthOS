from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from growthos.domain.enums import Role
from tests.conftest import (
    Identity,
    add_user_to_identity,
    create_identity,
    create_ready_media,
    csrf_headers,
    login,
)


def _create_portal_context() -> tuple[Identity, Identity, Identity]:
    admin = create_identity(
        slug="portal-visibility",
        email="admin-visibility@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica Visível",
    )
    reviewer = add_user_to_identity(
        admin,
        email="reviewer-visibility@example.com",
        role=Role.CLIENT_REVIEWER,
    )
    viewer = add_user_to_identity(
        admin,
        email="viewer-visibility@example.com",
        role=Role.VIEWER,
    )
    return admin, reviewer, viewer


def _generate_content(
    client: TestClient,
    headers: dict[str, str],
    business_id: UUID,
    objective: str,
    media_asset_id: UUID | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/contents/generate",
        json={
            "business_id": str(business_id),
            "objective": objective,
            "channel": "INSTAGRAM",
            "format": "FEED",
            **({"media_asset_id": str(media_asset_id)} if media_asset_id else {}),
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_business_portal_only_reads_content_released_to_the_client(
    client: TestClient,
) -> None:
    admin, reviewer, viewer = _create_portal_context()
    assert admin.business_id is not None
    headers = csrf_headers(login(client, admin))

    draft = _generate_content(client, headers, admin.business_id, "Rascunho privado")
    internal = _generate_content(
        client,
        headers,
        admin.business_id,
        "Revisão interna privada",
    )
    client.post(
        f"/api/v1/contents/{internal['id']}/submit-internal",
        headers=headers,
    )
    change_requested = _generate_content(
        client,
        headers,
        admin.business_id,
        "Revisão do cliente com ajuste",
    )
    approved = _generate_content(
        client,
        headers,
        admin.business_id,
        "Revisão do cliente aprovada",
        create_ready_media(admin),
    )
    for content in (change_requested, approved):
        assert (
            client.post(
                f"/api/v1/contents/{content['id']}/submit-internal",
                headers=headers,
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v1/contents/{content['id']}/send-to-client",
                headers=headers,
            ).status_code
            == 200
        )

    # O acesso interno da agência continua incluindo rascunhos e revisão interna.
    assert {item["id"] for item in client.get("/api/v1/contents").json()} == {
        draft["id"],
        internal["id"],
        change_requested["id"],
        approved["id"],
    }
    assert client.get(f"/api/v1/contents/{draft['id']}").status_code == 200
    assert client.get(f"/api/v1/contents/{internal['id']}").status_code == 200

    reviewer_client = TestClient(client.app)
    reviewer_headers = csrf_headers(login(reviewer_client, reviewer))
    listed_for_review = reviewer_client.get("/api/v1/contents")
    assert listed_for_review.status_code == 200
    assert {item["id"] for item in listed_for_review.json()} == {
        change_requested["id"],
        approved["id"],
    }
    assert reviewer_client.get(f"/api/v1/contents/{draft['id']}").status_code == 404
    assert reviewer_client.get(f"/api/v1/contents/{internal['id']}").status_code == 404
    assert reviewer_client.get(f"/api/v1/contents/{approved['id']}").status_code == 200

    changed = reviewer_client.post(
        f"/api/v1/contents/{change_requested['id']}/decisions/TEXT/request-changes",
        json={"comment": "Ajustar a chamada"},
        headers=reviewer_headers,
    )
    assert changed.status_code == 200, changed.text
    accepted_text = reviewer_client.post(
        f"/api/v1/contents/{approved['id']}/decisions/TEXT/approve",
        json={"comment": "Aprovado"},
        headers=reviewer_headers,
    )
    assert accepted_text.status_code == 200, accepted_text.text
    accepted = reviewer_client.post(
        f"/api/v1/contents/{approved['id']}/decisions/IMAGE/approve",
        json={"comment": "Imagem aprovada"},
        headers=reviewer_headers,
    )
    assert accepted.status_code == 200, accepted.text

    reviewer_statuses = {item["status"] for item in reviewer_client.get("/api/v1/contents").json()}
    assert reviewer_statuses == {"CHANGES_REQUESTED", "APPROVED"}

    viewer_client = TestClient(client.app)
    login(viewer_client, viewer)
    assert {item["id"] for item in viewer_client.get("/api/v1/contents").json()} == {
        change_requested["id"],
        approved["id"],
    }
    assert viewer_client.get(f"/api/v1/contents/{draft['id']}").status_code == 404
    assert viewer_client.get(f"/api/v1/contents/{internal['id']}").status_code == 404
    assert viewer_client.get(f"/api/v1/contents/{approved['id']}").status_code == 200


@pytest.mark.parametrize(
    "role",
    [Role.CLIENT_OWNER, Role.CLIENT_REVIEWER, Role.VIEWER],
)
def test_client_roles_do_not_receive_internal_brand_notes(
    client: TestClient,
    role: Role,
) -> None:
    admin = create_identity(
        slug=f"brand-notes-{role.value.lower()}",
        email=f"admin-{role.value.lower()}@example.com",
        role=Role.AGENCY_ADMIN,
        business_name=f"Brand {role.value}",
    )
    portal_user = add_user_to_identity(
        admin,
        email=f"portal-{role.value.lower()}@example.com",
        role=role,
    )
    assert admin.business_id is not None
    headers = csrf_headers(login(client, admin))
    stored = client.put(
        f"/api/v1/businesses/{admin.business_id}/brand-profile",
        json={
            "brand_name": "Marca pública",
            "description": "Descrição liberada",
            "internal_notes": "Não revelar ao portal",
        },
        headers=headers,
    )
    assert stored.status_code == 200, stored.text
    internal_view = client.get(f"/api/v1/businesses/{admin.business_id}/brand-profile")
    assert internal_view.status_code == 200
    assert internal_view.json()["internal_notes"] == "Não revelar ao portal"

    portal_client = TestClient(client.app)
    login(portal_client, portal_user)
    portal_view = portal_client.get(f"/api/v1/businesses/{admin.business_id}/brand-profile")
    assert portal_view.status_code == 200
    assert portal_view.json()["description"] == "Descrição liberada"
    assert portal_view.json()["internal_notes"] == ""
