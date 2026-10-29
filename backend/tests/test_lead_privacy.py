from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from growthos.config import Settings, get_settings
from growthos.config_errors import UnsafeConfigurationError
from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import AuditLog, BusinessLead, LandingPage, Membership
from growthos.pilot_client_cli import main as pilot_client_main
from tests.conftest import add_user_to_identity, create_identity, csrf_headers, login
from tests.test_landing import VILLA_PET_PAGE

PRIVACY = {
    "controller_name": "Villa Pet (razão social a confirmar)",
    "privacy_contact": "Canal oficial do estabelecimento (a confirmar)",
    "purpose": "Responder ao pedido de agendamento de banho e tosa feito pela página.",
    "legal_basis": "PROCEDIMENTOS_PRELIMINARES",
    "data_categories": ["Nome", "Telefone", "Serviço desejado"],
    "retention_days": 90,
    "notice_text": (
        "Usamos seu nome e telefone apenas para responder a este pedido de agendamento. "
        "Texto de exemplo para testes."
    ),
}
REAL_REQUEST = {
    "service_requested": "Banho",
    "price_item_label": "Pequeno",
    "preferred_period": "Manhã",
    "contact_name": "Tutor Fictício",
    "contact_phone": "(16) 90000-0000",
    "privacy_notice_version": 1,
    "privacy_accepted": True,
}


def _setup(client, slug: str = "privacy-agency"):
    agency = create_identity(
        slug=slug, email=f"{slug}@example.test", role=Role.AGENCY_ADMIN, business_name="Villa Pet"
    )
    owner = add_user_to_identity(agency, email=f"owner-{slug}@example.test", role=Role.CLIENT_OWNER)
    csrf = login(client, agency)
    base = f"/api/v1/businesses/{agency.business_id}"
    page = {**VILLA_PET_PAGE, "slug": f"{slug}-page"}
    assert (
        client.put(f"{base}/landing-page", headers=csrf_headers(csrf), json=page).status_code == 200
    )
    approved = client.post(
        f"{base}/landing-page/approve", headers=csrf_headers(csrf), json={"version": 1}
    )
    assert approved.status_code == 200
    return agency, owner, csrf, base, page["slug"]


def _open_collection(client) -> None:
    settings = get_settings().model_copy(
        update={
            "public_lead_collection_enabled": True,
            "public_lead_legal_review_approved": True,
            "public_lead_security_review_approved": True,
        }
    )
    client.app.dependency_overrides[get_settings] = lambda: settings


def _leave_demo_mode(slug: str) -> None:
    with get_session_factory()() as session:
        page = session.scalar(select(LandingPage).where(LandingPage.slug == slug))
        assert page is not None
        page.demo_mode = False
        session.commit()


def test_client_owner_sees_only_own_requests_and_cannot_edit_landing(client) -> None:
    agency, owner, _csrf, base, slug = _setup(client)
    other = create_identity(
        slug="other-org", email="other@example.test", role=Role.AGENCY_ADMIN, business_name="Outro"
    )
    reviewer = add_user_to_identity(
        agency, email="reviewer@example.test", role=Role.CLIENT_REVIEWER
    )
    client.post(
        f"/api/v1/public/landing/{slug}/demo-leads",
        json={"service_requested": "Banho", "preferred_period": "Tarde"},
    )

    owner_csrf = login(client, owner)
    leads = client.get(f"{base}/leads")
    assert leads.status_code == 200 and len(leads.json()) == 1
    summary = client.get(f"{base}/leads/summary").json()
    assert summary["awaiting_response"] == 1 and summary["real"] == 0
    lead_id = leads.json()[0]["id"]
    moved = client.patch(
        f"/api/v1/business-leads/{lead_id}",
        headers=csrf_headers(owner_csrf),
        json={"status": "HORARIO_OFERTADO", "next_action": "Aguardar confirmação do tutor"},
    )
    assert moved.status_code == 200 and moved.json()["status"] == "HORARIO_OFERTADO"
    edit = client.put(f"{base}/landing-page", headers=csrf_headers(owner_csrf), json=VILLA_PET_PAGE)
    assert edit.status_code == 403
    assert client.get(f"/api/v1/businesses/{other.business_id}/leads").status_code == 404

    reviewer_csrf = login(client, reviewer)
    assert client.get(f"{base}/leads").status_code == 200
    blocked = client.patch(
        f"/api/v1/business-leads/{lead_id}",
        headers=csrf_headers(reviewer_csrf),
        json={"status": "CONFIRMADO"},
    )
    assert blocked.status_code == 403
    with get_session_factory()() as session:
        update = session.scalar(
            select(AuditLog).where(
                AuditLog.action == "business_lead.updated",
                AuditLog.resource_id == UUID(lead_id),
            )
        )
    assert update is not None and update.actor_user_id == owner.user_id


def test_privacy_notice_is_drafted_by_agency_and_approved_only_by_owner(client) -> None:
    agency, owner, csrf, base, slug = _setup(client, "privacy-flow")
    assert client.get(f"/api/v1/public/landing/{slug}/intake").json() == {
        "collection_open": False,
        "notice": None,
        "availability": [],
    }
    saved = client.put(f"{base}/lead-privacy", headers=csrf_headers(csrf), json=PRIVACY)
    assert saved.status_code == 200 and saved.json()["status"] == "DRAFT"
    agency_approval = client.post(
        f"{base}/lead-privacy/approve",
        headers=csrf_headers(csrf),
        json={"version": 1, "acknowledged_not_legal_advice": True},
    )
    assert agency_approval.status_code == 403

    owner_csrf = login(client, owner)
    approve = f"{base}/lead-privacy/approve"
    no_ack = client.post(
        approve,
        headers=csrf_headers(owner_csrf),
        json={"version": 1, "acknowledged_not_legal_advice": False},
    )
    assert no_ack.status_code == 422
    stale = client.post(
        approve,
        headers=csrf_headers(owner_csrf),
        json={"version": 7, "acknowledged_not_legal_advice": True},
    )
    assert stale.status_code == 409
    ok = client.post(
        approve,
        headers=csrf_headers(owner_csrf),
        json={"version": 1, "acknowledged_not_legal_advice": True, "note": "Revisado"},
    )
    assert ok.status_code == 200 and ok.json()["status"] == "APPROVED"
    assert (
        client.put(
            f"{base}/lead-privacy", headers=csrf_headers(owner_csrf), json=PRIVACY
        ).status_code
        == 403
    )

    intake = client.get(f"/api/v1/public/landing/{slug}/intake").json()
    assert intake["collection_open"] is False  # coleta global segue desligada
    assert intake["notice"]["version"] == 1 and intake["notice"]["retention_days"] == 90

    agency_csrf = login(client, agency)
    edited = client.put(
        f"{base}/lead-privacy",
        headers=csrf_headers(agency_csrf),
        json={**PRIVACY, "retention_days": 30},
    )
    assert edited.json()["status"] == "DRAFT" and edited.json()["version"] == 2
    assert client.get(f"/api/v1/public/landing/{slug}/intake").json()["notice"] is None


def test_real_requests_need_all_gates_and_keep_contact_out_of_audit(client) -> None:
    agency, owner, csrf, base, slug = _setup(client, "real-gate")
    endpoint = f"/api/v1/public/landing/{slug}/requests"
    assert client.post(endpoint, json=REAL_REQUEST).status_code == 403  # tudo fechado
    client.put(f"{base}/lead-privacy", headers=csrf_headers(csrf), json=PRIVACY)
    owner_csrf = login(client, owner)
    client.post(
        f"{base}/lead-privacy/approve",
        headers=csrf_headers(owner_csrf),
        json={"version": 1, "acknowledged_not_legal_advice": True},
    )
    assert client.post(endpoint, json=REAL_REQUEST).status_code == 403  # flag global
    _open_collection(client)
    try:
        demo_blocked = client.post(endpoint, json=REAL_REQUEST)
        assert demo_blocked.status_code == 403 and "demonstração" in demo_blocked.json()["detail"]
        _leave_demo_mode(slug)

        assert (
            client.post(endpoint, json={**REAL_REQUEST, "privacy_accepted": False}).status_code
            == 422
        )
        assert (
            client.post(endpoint, json={**REAL_REQUEST, "privacy_notice_version": 2}).status_code
            == 422
        )
        assert client.post(endpoint, json={**REAL_REQUEST, "email": "x@y.z"}).status_code == 422
        first = client.post(endpoint, json=REAL_REQUEST)
        assert first.status_code == 202, first.text
        again = client.post(endpoint, json=REAL_REQUEST)
        assert again.json()["reference"] == first.json()["reference"]
        bot = client.post(
            endpoint, json={**REAL_REQUEST, "contact_phone": "16911112222", "website": "spam"}
        )
        assert bot.status_code == 202
    finally:
        client.app.dependency_overrides.pop(get_settings, None)

    with get_session_factory()() as session:
        leads = session.scalars(
            select(BusinessLead).where(BusinessLead.business_id == agency.business_id)
        ).all()
        audit = session.scalars(
            select(AuditLog).where(AuditLog.business_id == agency.business_id)
        ).all()
    assert len(leads) == 1
    lead = leads[0]
    assert lead.is_demo is False and lead.source == "LANDING_PAGE"
    assert lead.contact_phone == "16900000000"
    assert lead.privacy_notice_version == 1 and lead.consent_recorded_at is not None
    assert "business_lead.spam_dropped" in {entry.action for entry in audit}
    serialized = repr([entry.details for entry in audit])
    assert "Tutor Fictício" not in serialized and "90000" not in serialized


def test_export_anonymize_and_retention(client) -> None:
    agency, owner, csrf, base, slug = _setup(client, "rights")
    client.put(f"{base}/lead-privacy", headers=csrf_headers(csrf), json=PRIVACY)
    owner_csrf = login(client, owner)
    client.post(
        f"{base}/lead-privacy/approve",
        headers=csrf_headers(owner_csrf),
        json={"version": 1, "acknowledged_not_legal_advice": True},
    )
    _leave_demo_mode(slug)
    _open_collection(client)
    try:
        endpoint = f"/api/v1/public/landing/{slug}/requests"
        recent = client.post(endpoint, json=REAL_REQUEST).json()["reference"]
        old = client.post(endpoint, json={**REAL_REQUEST, "contact_phone": "16922223333"}).json()[
            "reference"
        ]
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
    with get_session_factory()() as session:
        aged = session.get(BusinessLead, UUID(old))
        assert aged is not None
        aged.created_at = datetime.now(UTC) - timedelta(days=120)
        session.commit()

    exported = client.get(f"/api/v1/business-leads/{recent}/export")
    assert exported.status_code == 200
    body = exported.json()
    assert body["lead"]["contact_name"] == "Tutor Fictício"
    assert body["controller_name"].startswith("Villa Pet")
    assert body["history"][0]["action"] == "business_lead.received"

    retention = f"{base}/leads/retention"
    dry = client.post(retention, headers=csrf_headers(owner_csrf), json={})
    assert dry.status_code == 200 and dry.json()["eligible"] == 1 and dry.json()["anonymized"] == 0
    run = client.post(retention, headers=csrf_headers(owner_csrf), json={"dry_run": False})
    assert run.json()["anonymized"] == 1

    anonymized = client.post(
        f"/api/v1/business-leads/{recent}/anonymize", headers=csrf_headers(owner_csrf)
    )
    assert anonymized.status_code == 200
    assert anonymized.json()["contact_name"] is None and anonymized.json()["anonymized_at"]
    with get_session_factory()() as session:
        for lead_id in (recent, old):
            lead = session.get(BusinessLead, UUID(lead_id))
            assert lead is not None and lead.contact_phone is None and lead.anonymized_at
        actions = {
            entry.action
            for entry in session.scalars(
                select(AuditLog).where(AuditLog.business_id == agency.business_id)
            )
        }
    assert {
        "business_lead.exported",
        "business_lead.anonymized",
        "business_lead.retention_run",
    } <= actions

    reviewer = add_user_to_identity(
        agency, email="rev-rights@example.test", role=Role.CLIENT_REVIEWER
    )
    login(client, reviewer)
    assert client.get(f"/api/v1/business-leads/{recent}/export").status_code == 403


def test_availability_starts_empty_and_rejects_invalid_windows(client) -> None:
    agency, owner, _csrf, base, _ = _setup(client, "availability")
    empty = client.get(f"{base}/availability").json()
    assert (
        empty["slots"] == [] and empty["confirmed_by_business"] is False and empty["version"] == 0
    )

    owner_csrf = login(client, owner)
    url = f"{base}/availability"
    overlap = {
        "slots": [
            {"weekday": 1, "start": "08:00", "end": "12:00"},
            {"weekday": 1, "start": "11:00", "end": "13:00"},
        ]
    }
    assert client.put(url, headers=csrf_headers(owner_csrf), json=overlap).status_code == 422
    assert (
        client.put(
            url, headers=csrf_headers(owner_csrf), json={"slots": [], "confirmed_by_business": True}
        ).status_code
        == 422
    )
    assert (
        client.put(
            url,
            headers=csrf_headers(owner_csrf),
            json={"slots": [{"weekday": 1, "start": "9h", "end": "10:00"}]},
        ).status_code
        == 422
    )
    saved = client.put(
        url,
        headers=csrf_headers(owner_csrf),
        json={
            "slots": [{"weekday": 5, "start": "08:00", "end": "12:00", "label": "Sábado"}],
            "confirmed_by_business": True,
        },
    )
    assert saved.status_code == 200 and saved.json()["version"] == 1
    with get_session_factory()() as session:
        entry = session.scalar(
            select(AuditLog).where(AuditLog.action == "business_availability.saved")
        )
    assert entry is not None and entry.actor_user_id == owner.user_id

    reviewer = add_user_to_identity(agency, email="rev-av@example.test", role=Role.CLIENT_REVIEWER)
    reviewer_csrf = login(client, reviewer)
    assert (
        client.put(url, headers=csrf_headers(reviewer_csrf), json={"slots": []}).status_code == 403
    )


def test_collection_flag_requires_declared_reviews() -> None:
    with pytest.raises(UnsafeConfigurationError):
        Settings(public_lead_collection_enabled=True)
    assert Settings(
        public_lead_collection_enabled=True,
        public_lead_legal_review_approved=True,
        public_lead_security_review_approved=True,
    ).public_lead_collection_enabled


def test_pilot_client_cli_creates_scoped_owner_idempotently(monkeypatch) -> None:
    agency = create_identity(
        slug="pilot-org",
        email="pilot@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Villa Pet",
    )
    assert pilot_client_main(["--org", "pilot-org", "--business", "Villa Pet"]) == 0
    assert pilot_client_main(["--org", "pilot-org", "--business", "Villa Pet"]) == 0
    assert pilot_client_main(["--org", "pilot-org", "--business", "Inexistente"]) == 1
    with get_session_factory()() as session:
        owners = session.scalars(
            select(Membership).where(
                Membership.organization_id == agency.organization_id,
                Membership.role == Role.CLIENT_OWNER,
            )
        ).all()
    assert len(owners) == 1 and owners[0].business_id == agency.business_id
