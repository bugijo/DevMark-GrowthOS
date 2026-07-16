from uuid import UUID

from fastapi.testclient import TestClient

from growthos.domain.enums import Role
from tests.conftest import create_identity, create_ready_media, csrf_headers, login


def _prepare_content(client: TestClient) -> tuple[dict[str, object], dict[str, str]]:
    admin = create_identity(
        slug="vertical",
        email="admin-vertical@example.com",
        role=Role.AGENCY_ADMIN,
    )
    csrf = login(client, admin)
    headers = csrf_headers(csrf)
    business_response = client.post(
        "/api/v1/businesses",
        json={"name": "Clínica Feliz", "segment": "Veterinária"},
        headers=headers,
    )
    assert business_response.status_code == 201
    business = business_response.json()
    brand = client.put(
        f"/api/v1/businesses/{business['id']}/brand-profile",
        json={
            "brand_name": "Clínica Feliz",
            "public_name": "Clínica Feliz",
            "description": "Clínica veterinária fictícia",
            "segment": "Veterinária",
            "audience": "Tutores de cães e gatos",
            "primary_colors": ["#123456"],
            "tone_of_voice": "acolhedor",
            "preferred_words": ["cuidado"],
            "forbidden_words": ["cura garantida"],
            "slogan": "Cuidado responsável",
            "differentiators": ["atendimento humanizado"],
            "services": ["vacinação"],
            "contacts": {"phone": "(00) 0000-0000"},
            "links": ["https://example.com"],
            "calls_to_action": ["Agende uma avaliação."],
            "internal_notes": "Apenas dados fictícios",
        },
        headers=headers,
    )
    assert brand.status_code == 200, brand.text
    reviewer_payload = {
        "name": "Cliente Clínica Feliz",
        "email": "client@clinicafeliz.local",
        "password": "client-password-123",
    }
    reviewer = client.post(
        f"/api/v1/businesses/{business['id']}/reviewers",
        json=reviewer_payload,
        headers=headers,
    )
    assert reviewer.status_code == 201, reviewer.text
    generated = client.post(
        "/api/v1/contents/generate",
        json={
            "business_id": business["id"],
            "objective": "Explicar a vacinação preventiva",
            "channel": "INSTAGRAM",
            "format": "FEED",
            "media_asset_id": str(create_ready_media(admin, business_id=UUID(business["id"]))),
        },
        headers=headers,
    )
    assert generated.status_code == 201, generated.text
    content = generated.json()
    assert content["status"] == "DRAFT"
    assert content["current_version"]["provider_name"] == "mock"
    assert "Clínica Feliz" in content["current_version"]["title"]
    assert (
        client.post(f"/api/v1/contents/{content['id']}/submit-internal", headers=headers).json()[
            "status"
        ]
        == "INTERNAL_REVIEW"
    )
    sent = client.post(f"/api/v1/contents/{content['id']}/send-to-client", headers=headers)
    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "CLIENT_REVIEW"
    repeated_send = client.post(
        f"/api/v1/contents/{content['id']}/send-to-client",
        headers=headers,
    )
    assert repeated_send.status_code == 409
    return content, reviewer_payload


def test_vertical_flow_approval_notifications_and_audit(client: TestClient) -> None:
    content, reviewer = _prepare_content(client)
    reviewer_client = TestClient(client.app)
    login_response = reviewer_client.post(
        "/api/v1/auth/login",
        json={"email": reviewer["email"], "password": reviewer["password"]},
    )
    assert login_response.status_code == 200, login_response.text
    csrf = login_response.json()["csrf_token"]
    notifications = reviewer_client.get("/api/v1/notifications").json()
    assert len(notifications) == 1
    assert notifications[0]["resource_id"] == content["id"]
    read = reviewer_client.post(
        f"/api/v1/notifications/{notifications[0]['id']}/read",
        headers=csrf_headers(csrf),
    )
    assert read.status_code == 200
    text_approved = reviewer_client.post(
        f"/api/v1/contents/{content['id']}/decisions/TEXT/approve",
        json={"comment": "Aprovado pela clínica"},
        headers=csrf_headers(csrf),
    )
    assert text_approved.status_code == 200, text_approved.text
    assert text_approved.json()["status"] == "CLIENT_REVIEW"
    approved = reviewer_client.post(
        f"/api/v1/contents/{content['id']}/decisions/IMAGE/approve",
        json={"comment": "Imagem aprovada pela clínica"},
        headers=csrf_headers(csrf),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"

    audit = client.get("/api/v1/audit-logs").json()
    actions = {entry["action"] for entry in audit}
    assert "content.generated" in actions
    assert "content.sent_to_client" in actions
    assert "content.approved_by_client" in actions
    assert "notification.created" in actions
    admin_notifications = client.get("/api/v1/notifications").json()
    assert any(item["type"] == "CONTENT_DECISION" for item in admin_notifications)


def test_request_changes_requires_real_agency_revision_before_resubmission(
    client: TestClient,
) -> None:
    content, reviewer = _prepare_content(client)
    reviewer_client = TestClient(client.app)
    login_response = reviewer_client.post(
        "/api/v1/auth/login",
        json={"email": reviewer["email"], "password": reviewer["password"]},
    )
    csrf = login_response.json()["csrf_token"]
    changed = reviewer_client.post(
        f"/api/v1/contents/{content['id']}/decisions/TEXT/request-changes",
        json={"comment": "Ajustar a chamada final"},
        headers=csrf_headers(csrf),
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "CHANGES_REQUESTED"
    assert changed.json()["change_request_comment"] == "Ajustar a chamada final"
    assert changed.json()["current_version"]["version_number"] == 1
    assert changed.json()["current_version"]["id"] == content["current_version"]["id"]

    admin_csrf = client.get("/api/v1/auth/me").json()["csrf_token"]
    bypass_revision = client.post(
        f"/api/v1/contents/{content['id']}/submit-internal",
        headers=csrf_headers(admin_csrf),
    )
    assert bypass_revision.status_code == 409

    unchanged_payload = {
        "title": content["current_version"]["title"],
        "caption": content["current_version"]["caption"],
        "cta": content["current_version"]["cta"],
    }
    unchanged = client.post(
        f"/api/v1/contents/{content['id']}/revisions",
        json=unchanged_payload,
        headers=csrf_headers(admin_csrf),
    )
    assert unchanged.status_code == 409

    revision_payload = {
        **unchanged_payload,
        "cta": "Agende uma conversa com a equipe.",
    }
    revised = client.post(
        f"/api/v1/contents/{content['id']}/revisions",
        json=revision_payload,
        headers=csrf_headers(admin_csrf),
    )
    assert revised.status_code == 200, revised.text
    assert revised.json()["status"] == "DRAFT"
    assert revised.json()["change_request_comment"] is None
    assert revised.json()["current_version"]["version_number"] == 2
    assert revised.json()["current_version"]["id"] != content["current_version"]["id"]
    assert revised.json()["current_version"]["cta"] == revision_payload["cta"]
    assert reviewer_client.get(f"/api/v1/contents/{content['id']}").status_code == 404

    submitted = client.post(
        f"/api/v1/contents/{content['id']}/submit-internal",
        headers=csrf_headers(admin_csrf),
    )
    assert submitted.status_code == 200
    sent = client.post(
        f"/api/v1/contents/{content['id']}/send-to-client",
        headers=csrf_headers(admin_csrf),
    )
    assert sent.status_code == 200
    text_approved = reviewer_client.post(
        f"/api/v1/contents/{content['id']}/decisions/TEXT/approve",
        json={"comment": "Nova versão aprovada"},
        headers=csrf_headers(csrf),
    )
    assert text_approved.status_code == 200, text_approved.text
    assert text_approved.json()["status"] == "CLIENT_REVIEW"
    approved = reviewer_client.post(
        f"/api/v1/contents/{content['id']}/decisions/IMAGE/approve",
        json={"comment": "Nova imagem aprovada"},
        headers=csrf_headers(csrf),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["current_version"]["version_number"] == 2

    actions = {entry["action"] for entry in client.get("/api/v1/audit-logs").json()}
    assert "content.revision_created" in actions
