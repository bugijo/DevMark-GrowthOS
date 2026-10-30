from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import AuditLog, BusinessLead
from tests.conftest import create_identity, csrf_headers, login

VILLA_PET_PAGE = {
    "slug": "villa-pet-demo",
    "headline": "Banho e tosa com cuidado e agendamento",
    "subheadline": "Atendimento conforme porte, pelagem e necessidade do seu pet.",
    "cta_label": "Agendar banho e tosa",
    "address": "Rua Expedicionário Solano, 510 — Sertãozinho/SP",
    "contact_channel": "WhatsApp comercial (a confirmar)",
    "highlights": ["Atendimento sob agendamento", "Orientação conforme o porte"],
    "service_options": ["Banho", "Banho e tosa"],
    "price_items": [
        {"label": "Pequeno", "price_cents": 5500},
        {"label": "Médio", "price_cents": 7500},
        {"label": "Grande", "price_cents": 9500},
    ],
    "price_disclaimer": "Valores de referência, sujeitos a confirmação pela equipe.",
}


def _agency_with_business(slug: str = "landing-agency"):
    return create_identity(
        slug=slug,
        email=f"{slug}@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Villa Pet",
    )


def test_page_is_private_until_human_approval_and_edit_resets_it(client) -> None:
    owner = _agency_with_business()
    csrf = login(client, owner)
    base = f"/api/v1/businesses/{owner.business_id}/landing-page"

    saved = client.put(base, headers=csrf_headers(csrf), json=VILLA_PET_PAGE)
    assert saved.status_code == 200, saved.text
    assert saved.json()["status"] == "DRAFT"
    assert saved.json()["demo_mode"] is True
    assert client.get("/api/v1/public/landing/villa-pet-demo").status_code == 404

    stale = client.post(f"{base}/approve", headers=csrf_headers(csrf), json={"version": 99})
    assert stale.status_code == 409
    approved = client.post(f"{base}/approve", headers=csrf_headers(csrf), json={"version": 1})
    assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"

    public = client.get("/api/v1/public/landing/villa-pet-demo")
    assert public.status_code == 200
    body = public.json()
    assert body["business_name"] == "Villa Pet"
    assert [item["price_cents"] for item in body["price_items"]] == [5500, 7500, 9500]
    assert "organization_id" not in body and "approved_by_user_id" not in body

    revoked = client.post(f"{base}/revoke", headers=csrf_headers(csrf))
    assert revoked.status_code == 200 and revoked.json()["status"] == "DRAFT"
    assert client.get("/api/v1/public/landing/villa-pet-demo").status_code == 404
    assert (
        client.post(
            "/api/v1/public/landing/villa-pet-demo/demo-leads",
            json={"service_requested": "Banho", "preferred_period": "Manhã"},
        ).status_code
        == 404
    )
    reapproved = client.post(f"{base}/approve", headers=csrf_headers(csrf), json={"version": 1})
    assert reapproved.json()["status"] == "APPROVED"
    with get_session_factory()() as session:
        actions = set(
            session.scalars(select(AuditLog.action).where(AuditLog.resource_type == "landing_page"))
        )
    assert {"landing_page.created", "landing_page.approved", "landing_page.revoked"} <= actions

    edited = client.put(
        base, headers=csrf_headers(csrf), json={**VILLA_PET_PAGE, "headline": "Novo título"}
    )
    assert edited.json()["status"] == "DRAFT" and edited.json()["version"] == 2
    assert client.get("/api/v1/public/landing/villa-pet-demo").status_code == 404


def test_prices_require_disclaimer_and_slug_is_unique_across_tenants(client) -> None:
    owner = _agency_with_business("landing-a")
    other = _agency_with_business("landing-b")
    csrf = login(client, owner)
    no_disclaimer = {**VILLA_PET_PAGE, "price_disclaimer": ""}
    response = client.put(
        f"/api/v1/businesses/{owner.business_id}/landing-page",
        headers=csrf_headers(csrf),
        json=no_disclaimer,
    )
    assert response.status_code == 422
    assert (
        client.put(
            f"/api/v1/businesses/{owner.business_id}/landing-page",
            headers=csrf_headers(csrf),
            json=VILLA_PET_PAGE,
        ).status_code
        == 200
    )
    csrf = login(client, other)
    clash = client.put(
        f"/api/v1/businesses/{other.business_id}/landing-page",
        headers=csrf_headers(csrf),
        json=VILLA_PET_PAGE,
    )
    assert clash.status_code == 409
    assert client.get(f"/api/v1/businesses/{owner.business_id}/landing-page").status_code == 404


def test_demo_form_rejects_personal_data_and_records_demo_lead(client) -> None:
    owner = _agency_with_business("landing-demo")
    csrf = login(client, owner)
    base = f"/api/v1/businesses/{owner.business_id}/landing-page"
    client.put(base, headers=csrf_headers(csrf), json=VILLA_PET_PAGE)
    client.post(f"{base}/approve", headers=csrf_headers(csrf), json={"version": 1})
    client.cookies.clear()

    url = "/api/v1/public/landing/villa-pet-demo/demo-leads"
    choice = {
        "service_requested": "Banho e tosa",
        "price_item_label": "Médio",
        "preferred_period": "Manhã",
        "heard_from": "INSTAGRAM_POST",
    }
    for personal in ({"name": "Fulano"}, {"whatsapp": "16999999999"}, {"email": "a@b.co"}):
        assert client.post(url, json={**choice, **personal}).status_code == 422
    assert client.post(url, json={**choice, "service_requested": "Hotel"}).status_code == 422
    assert client.post(url, json={**choice, "price_item_label": "Gigante"}).status_code == 422

    receipt = client.post(url, json=choice)
    assert receipt.status_code == 202, receipt.text
    assert "Nenhum contato" in receipt.json()["message"]

    with get_session_factory()() as session:
        lead = session.get(BusinessLead, UUID(receipt.json()["reference"]))
        assert lead is not None
        assert lead.is_demo is True and lead.source == "LANDING_DEMO"
        assert lead.reference_price_cents == 7500 and lead.status == "NOVO"
        assert lead.next_action
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "business_lead.demo_created")
        )
        assert audit is not None and audit.details == {"source": "LANDING_DEMO", "is_demo": True}


def test_follow_up_transitions_summary_and_tenant_isolation(client) -> None:
    owner = _agency_with_business("landing-follow")
    other = _agency_with_business("landing-other")
    csrf = login(client, owner)
    client.put(
        f"/api/v1/businesses/{owner.business_id}/landing-page",
        headers=csrf_headers(csrf),
        json=VILLA_PET_PAGE,
    )
    created = client.post(
        f"/api/v1/businesses/{owner.business_id}/leads",
        headers=csrf_headers(csrf),
        json={
            "source": "INSTAGRAM_STORY",
            "service_requested": "Banho",
            "price_item_label": "Pequeno",
            "preferred_period": "Tarde",
            "notes": "Exercício fictício",
        },
    )
    assert created.status_code == 201, created.text
    lead = created.json()
    assert lead["is_demo"] is True and lead["reference_price_cents"] == 5500
    lead_url = f"/api/v1/business-leads/{lead['id']}"

    skip = client.patch(lead_url, headers=csrf_headers(csrf), json={"status": "REALIZADO"})
    assert skip.status_code == 409
    overdue = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    moved = client.patch(
        lead_url,
        headers=csrf_headers(csrf),
        json={
            "status": "HORARIO_OFERTADO",
            "next_action": "Aguardar confirmação do horário",
            "next_action_due_at": overdue,
        },
    )
    assert moved.status_code == 200 and moved.json()["status"] == "HORARIO_OFERTADO"

    summary = client.get(f"/api/v1/businesses/{owner.business_id}/leads/summary").json()
    assert summary["total"] == 1 and summary["demo"] == 1
    assert summary["by_status"] == {"HORARIO_OFERTADO": 1}
    assert summary["overdue_next_actions"] == 1
    assert summary["landing_status"] == "DRAFT"

    csrf_other = login(client, other)
    assert client.get(f"/api/v1/businesses/{owner.business_id}/leads").status_code == 404
    assert (
        client.patch(lead_url, headers=csrf_headers(csrf_other), json={"notes": "x"}).status_code
        == 404
    )
