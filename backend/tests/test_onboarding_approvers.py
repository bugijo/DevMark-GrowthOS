from fastapi.testclient import TestClient

from growthos.domain.enums import Role
from tests.conftest import add_user_to_identity, create_identity, login


def test_strategist_lists_only_scoped_client_approvers(client: TestClient) -> None:
    strategist = create_identity(
        slug="onboarding-approvers",
        email="strategist-approvers@example.com",
        role=Role.STRATEGIST,
        business_name="Clínica dos aprovadores",
    )
    reviewer = add_user_to_identity(
        strategist,
        email="reviewer-approvers@example.com",
        role=Role.CLIENT_REVIEWER,
    )
    owner = add_user_to_identity(
        strategist,
        email="owner-approvers@example.com",
        role=Role.CLIENT_OWNER,
    )
    outsider = create_identity(
        slug="onboarding-approvers-other",
        email="other-admin@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Outra clínica",
    )
    add_user_to_identity(
        outsider,
        email="other-reviewer@example.com",
        role=Role.CLIENT_REVIEWER,
    )
    login(client, strategist)

    response = client.get(f"/api/v1/businesses/{strategist.business_id}/onboarding/approvers")

    assert response.status_code == 200, response.text
    assert {item["membership_id"] for item in response.json()} == {
        str(reviewer.membership_id),
        str(owner.membership_id),
    }
    assert {item["email"] for item in response.json()} == {
        reviewer.email,
        owner.email,
    }
    assert all(item["business_id"] == str(strategist.business_id) for item in response.json())

    cross_tenant = client.get(f"/api/v1/businesses/{outsider.business_id}/onboarding/approvers")
    assert cross_tenant.status_code == 404


def test_client_reviewer_cannot_enumerate_onboarding_approvers(
    client: TestClient,
) -> None:
    agency = create_identity(
        slug="onboarding-approvers-client",
        email="agency-approvers@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica privada",
    )
    reviewer = add_user_to_identity(
        agency,
        email="private-reviewer@example.com",
        role=Role.CLIENT_REVIEWER,
    )
    login(client, reviewer)

    response = client.get(f"/api/v1/businesses/{agency.business_id}/onboarding/approvers")

    assert response.status_code == 403
