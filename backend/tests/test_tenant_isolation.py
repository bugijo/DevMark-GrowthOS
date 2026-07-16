from fastapi.testclient import TestClient

from growthos.domain.enums import Role
from tests.conftest import add_user_to_identity, create_identity, csrf_headers, login


def test_queries_and_mutations_are_isolated_between_organizations(client: TestClient) -> None:
    org_a = create_identity(
        slug="org-a",
        email="admin-a@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Business A",
    )
    org_b = create_identity(
        slug="org-b",
        email="admin-b@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Business B",
    )
    reviewer_a = add_user_to_identity(
        org_a,
        email="reviewer-a@example.com",
        role=Role.CLIENT_REVIEWER,
    )

    csrf_a = login(client, org_a)
    assert client.get(f"/api/v1/businesses/{org_b.business_id}").status_code == 404
    cross_brand = client.put(
        f"/api/v1/businesses/{org_b.business_id}/brand-profile",
        json={"brand_name": "Cross tenant"},
        headers=csrf_headers(csrf_a),
    )
    assert cross_brand.status_code == 404
    cross_generation = client.post(
        "/api/v1/contents/generate",
        json={
            "business_id": str(org_b.business_id),
            "objective": "Acesso indevido",
            "channel": "INSTAGRAM",
            "format": "FEED",
        },
        headers=csrf_headers(csrf_a),
    )
    assert cross_generation.status_code == 404
    assert {item["id"] for item in client.get("/api/v1/businesses").json()} == {
        str(org_a.business_id)
    }

    other_client = TestClient(client.app)
    csrf_b = login(other_client, org_b)
    content_b_response = other_client.post(
        "/api/v1/contents/generate",
        json={
            "business_id": str(org_b.business_id),
            "objective": "Conteúdo da organização B",
            "channel": "INSTAGRAM",
            "format": "FEED",
        },
        headers=csrf_headers(csrf_b),
    )
    assert content_b_response.status_code == 201
    content_b = content_b_response.json()

    reviewer_client = TestClient(client.app)
    reviewer_csrf = login(reviewer_client, reviewer_a)
    assert reviewer_client.get(f"/api/v1/contents/{content_b['id']}").status_code == 404
    cross_approval = reviewer_client.post(
        f"/api/v1/contents/{content_b['id']}/decisions/TEXT/approve",
        json={},
        headers=csrf_headers(reviewer_csrf),
    )
    assert cross_approval.status_code == 404


def test_client_reviewer_cannot_create_another_reviewer(client: TestClient) -> None:
    reviewer = create_identity(
        slug="client-role",
        email="reviewer-role@example.com",
        role=Role.CLIENT_REVIEWER,
        business_name="Client Business",
    )
    csrf = login(client, reviewer)
    response = client.post(
        f"/api/v1/businesses/{reviewer.business_id}/reviewers",
        json={
            "name": "Not allowed",
            "email": "not-allowed@example.com",
            "password": "not-allowed-123",
        },
        headers=csrf_headers(csrf),
    )
    assert response.status_code == 403
