from uuid import UUID

from sqlalchemy import func, select

from growthos.config import get_settings
from growthos.database import get_session_factory
from growthos.models import AuditLog, BusinessLead, LandingDailyMetric
from tests.conftest import csrf_headers, login
from tests.test_landing import VILLA_PET_PAGE
from tests.test_lead_privacy import _leave_demo_mode, _open_collection, _setup

WHATSAPP = "5516900000000"  # fictício, só para teste


def _with_whatsapp(client, csrf, base, slug):
    page = {**VILLA_PET_PAGE, "slug": slug, "whatsapp_number": "+55 (16) 90000-0000"}
    saved = client.put(f"{base}/landing-page", headers=csrf_headers(csrf), json=page)
    assert saved.status_code == 200, saved.text
    assert saved.json()["whatsapp_number"] == WHATSAPP
    # Mudar o número é mudança de conteúdo: volta para rascunho e exige nova aprovação.
    assert saved.json()["status"] == "DRAFT"
    assert client.get(f"/api/v1/public/landing/{slug}").status_code == 404
    approved = client.post(
        f"{base}/landing-page/approve",
        headers=csrf_headers(csrf),
        json={"version": saved.json()["version"]},
    )
    assert approved.status_code == 200


def _confirm_tuesday_morning(client, csrf, base):
    saved = client.put(
        f"{base}/availability",
        headers=csrf_headers(csrf),
        json={
            "slots": [{"weekday": 1, "start": "08:00", "end": "11:30"}],
            "confirmed_by_business": True,
        },
    )
    assert saved.status_code == 200, saved.text


def test_whatsapp_number_comes_from_config_and_is_validated(client) -> None:
    _agency, _owner, csrf, base, slug = _setup(client, "wa-config")
    assert client.get(f"/api/v1/public/landing/{slug}").json()["whatsapp_number"] == ""
    invalid = client.put(
        f"{base}/landing-page",
        headers=csrf_headers(csrf),
        json={**VILLA_PET_PAGE, "slug": slug, "whatsapp_number": "abc123"},
    )
    assert invalid.status_code == 422
    _with_whatsapp(client, csrf, base, slug)
    assert client.get(f"/api/v1/public/landing/{slug}").json()["whatsapp_number"] == WHATSAPP


def test_whatsapp_click_is_only_an_aggregate_count(client) -> None:
    agency, _owner, csrf, base, slug = _setup(client, "wa-click")
    # Sem número configurado não há botão, logo nada a contar.
    no_number = client.post(
        f"/api/v1/public/landing/{slug}/events", json={"event": "whatsapp_click"}
    )
    assert no_number.status_code == 404
    _with_whatsapp(client, csrf, base, slug)
    client.cookies.clear()
    for _ in range(3):
        response = client.post(
            f"/api/v1/public/landing/{slug}/events", json={"event": "whatsapp_click"}
        )
        assert response.status_code == 204
    # Nenhum dado extra é aceito junto do evento.
    rejected = client.post(
        f"/api/v1/public/landing/{slug}/events",
        json={"event": "whatsapp_click", "phone": "16900000000"},
    )
    assert rejected.status_code == 422
    assert (
        client.post(
            f"/api/v1/public/landing/{slug}/events", json={"event": "page_view"}
        ).status_code
        == 422
    )

    with get_session_factory()() as session:
        rows = session.scalars(
            select(LandingDailyMetric).where(LandingDailyMetric.business_id == agency.business_id)
        ).all()
        assert [(row.event, row.count) for row in rows] == [("whatsapp_click", 3)]
        leads = session.scalar(
            select(func.count())
            .select_from(BusinessLead)
            .where(BusinessLead.business_id == agency.business_id)
        )
        assert leads == 0

    login(client, agency)
    summary = client.get(f"{base}/leads/summary").json()
    assert summary["whatsapp_clicks_7d"] == 3
    assert summary["total"] == 0


def test_form_offers_only_confirmed_days_and_never_confirms(client) -> None:
    _agency, _owner, csrf, base, slug = _setup(client, "wa-form")
    intake = client.get(f"/api/v1/public/landing/{slug}/intake").json()
    assert intake["availability"] == []
    choice = {"service_requested": "Banho", "price_item_label": "Pequeno"}
    # Sem agenda confirmada, nenhum dia pode ser escolhido.
    no_days = client.post(
        f"/api/v1/public/landing/{slug}/demo-leads",
        json={**choice, "preferred_period": "Manhã", "preferred_weekday": 1},
    )
    assert no_days.status_code == 422

    _confirm_tuesday_morning(client, csrf, base)
    intake = client.get(f"/api/v1/public/landing/{slug}/intake").json()
    assert intake["availability"] == [{"weekday": 1, "periods": ["Manhã"]}]
    afternoon = client.post(
        f"/api/v1/public/landing/{slug}/demo-leads",
        json={**choice, "preferred_period": "Tarde", "preferred_weekday": 1},
    )
    assert afternoon.status_code == 422
    accepted = client.post(
        f"/api/v1/public/landing/{slug}/demo-leads",
        json={**choice, "preferred_period": "Manhã", "preferred_weekday": 1},
    )
    assert accepted.status_code == 202, accepted.text
    # O formulário demonstrativo continua recusando qualquer dado pessoal.
    personal = client.post(
        f"/api/v1/public/landing/{slug}/demo-leads",
        json={**choice, "preferred_period": "Manhã", "contact_name": "Tutor"},
    )
    assert personal.status_code == 422

    leads = client.get(f"{base}/leads").json()
    assert len(leads) == 1
    assert leads[0]["preferred_period"] == "Terça-feira · Manhã"
    assert leads[0]["status"] == "NOVO"
    assert leads[0]["is_demo"] is True
    assert leads[0]["contact_name"] is None


def test_real_request_with_day_still_needs_gates(client) -> None:
    _agency, owner, csrf, base, slug = _setup(client, "wa-real")
    _confirm_tuesday_morning(client, csrf, base)
    request = {
        "service_requested": "Banho",
        "price_item_label": "Pequeno",
        "preferred_period": "Manhã",
        "preferred_weekday": 1,
        "contact_name": "Tutor Fictício",
        "contact_phone": "(16) 90000-0000",
        "privacy_notice_version": 1,
        "privacy_accepted": True,
    }
    blocked = client.post(f"/api/v1/public/landing/{slug}/requests", json=request)
    assert blocked.status_code == 403

    privacy = {
        "controller_name": "Villa Pet",
        "privacy_contact": "privacidade@villapet.local",
        "purpose": "Responder pedidos de agendamento",
        "legal_basis": "PROCEDIMENTOS_PRELIMINARES",
        "data_categories": ["nome", "telefone"],
        "retention_days": 90,
        "notice_text": "Usamos nome e telefone só para responder ao seu pedido.",
    }
    assert (
        client.put(f"{base}/lead-privacy", headers=csrf_headers(csrf), json=privacy).status_code
        == 200
    )
    owner_csrf = login(client, owner)
    approved = client.post(
        f"{base}/lead-privacy/approve",
        headers=csrf_headers(owner_csrf),
        json={"version": 1, "acknowledged_not_legal_advice": True},
    )
    assert approved.status_code == 200, approved.text
    _open_collection(client)
    try:
        _leave_demo_mode(slug)
        client.cookies.clear()
        received = client.post(f"/api/v1/public/landing/{slug}/requests", json=request)
        assert received.status_code == 202, received.text
    finally:
        client.app.dependency_overrides.pop(get_settings, None)

    login(client, owner)
    lead = client.get(f"{base}/leads").json()[0]
    assert lead["preferred_period"] == "Terça-feira · Manhã"
    assert lead["status"] == "NOVO"


def test_team_confirms_manually_with_audit_history(client) -> None:
    _agency, owner, csrf, base, _slug = _setup(client, "wa-confirm")
    created = client.post(
        f"{base}/leads",
        headers=csrf_headers(csrf),
        json={
            "source": "WHATSAPP_DIRETO",
            "service_requested": "Banho",
            "preferred_period": "Manhã",
        },
    )
    assert created.status_code == 201
    lead_id = created.json()["id"]

    owner_csrf = login(client, owner)
    confirmed = client.patch(
        f"/api/v1/business-leads/{lead_id}",
        headers=csrf_headers(owner_csrf),
        json={"status": "CONFIRMADO"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "CONFIRMADO"
    back = client.patch(
        f"/api/v1/business-leads/{lead_id}",
        headers=csrf_headers(owner_csrf),
        json={"status": "NOVO"},
    )
    assert back.status_code == 409

    history = client.get(f"/api/v1/business-leads/{lead_id}/history")
    assert history.status_code == 200
    entries = history.json()
    assert [entry["action"] for entry in entries] == [
        "business_lead.created",
        "business_lead.updated",
    ]
    assert entries[1]["changes"] == {"status": "NOVO->CONFIRMADO"}
    assert entries[1]["actor"] != "Página pública"

    with get_session_factory()() as session:
        actions = session.scalars(
            select(AuditLog.action).where(AuditLog.resource_id == UUID(lead_id))
        ).all()
        assert not any("message" in action or "notification" in action for action in actions)


def test_lead_history_is_isolated_between_businesses(client) -> None:
    _agency, _owner, csrf, base, _slug = _setup(client, "wa-iso-a")
    created = client.post(
        f"{base}/leads",
        headers=csrf_headers(csrf),
        json={"source": "WHATSAPP_DIRETO", "service_requested": "Banho"},
    )
    lead_id = created.json()["id"]
    other, _other_owner, _other_csrf, _other_base, _other_slug = _setup(client, "wa-iso-b")
    login(client, other)
    assert client.get(f"/api/v1/business-leads/{lead_id}/history").status_code == 404
