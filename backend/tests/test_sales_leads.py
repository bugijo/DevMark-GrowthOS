from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from growthos.config import get_settings
from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import AuditLog, RetentionPolicy, SalesLead
from growthos.rate_limit import reset_login_rate_limiter
from growthos.services.sales import classify_request
from tests.conftest import create_identity, csrf_headers, login


def enabled_quote_settings(attempts=10):
    return get_settings().model_copy(
        update={
            "public_quote_intake_enabled": True,
            "public_quote_target_organization_slug": "devmarkia-test",
            "public_quote_privacy_notice_url": "https://example.test/privacy",
            "public_quote_privacy_notice_version": "test-v1",
            "public_quote_legal_review_approved": True,
            "public_quote_security_review_approved": True,
            "public_quote_rate_limit_attempts": attempts,
        }
    )


def test_public_quote_is_disabled_by_default_and_does_not_persist(client):
    identity = create_identity(
        slug="devmarkia-test", email="owner@example.test", role=Role.AGENCY_ADMIN
    )
    del identity
    config = client.get("/api/v1/public/quote-requests/config")
    assert config.status_code == 200 and config.json() == {
        "enabled": False,
        "privacy_notice_url": None,
        "privacy_notice_version": None,
    }
    response = client.post(
        "/api/v1/public/quote-requests",
        json={
            "name": "Pessoa Teste",
            "goal": "Landing page",
            "email": "pessoa@example.test",
            "privacy_consent": True,
        },
    )
    assert response.status_code == 404
    with get_session_factory()() as session:
        assert session.scalar(select(SalesLead.id)) is None


def test_scope_classifier_routes_uncertain_and_excluded_work_to_review():
    assert classify_request("Landing page comercial para meu serviço")[0] == "IN_SCOPE_LANDING_PAGE"
    assert classify_request("Loja virtual com checkout")[0] == "OUT_OF_SCOPE"
    assert classify_request("Preciso melhorar minha presença digital")[0] == "HUMAN_REVIEW"


def test_public_quote_consent_idempotency_and_minimal_receipt(client, monkeypatch, caplog):
    create_identity(slug="devmarkia-test", email="owner@example.test", role=Role.AGENCY_ADMIN)
    from growthos.config import get_settings
    from growthos.main import app

    monkeypatch.setitem(app.dependency_overrides, get_settings, enabled_quote_settings)
    reset_login_rate_limiter()
    body = {
        "name": "Pessoa Fictícia",
        "company": "Empresa Exemplo",
        "goal": "Criar landing",
        "email": "pessoa@example.test",
        "privacy_consent": True,
    }
    headers = {"Idempotency-Key": "quote-test-key-0001"}
    first = client.post("/api/v1/public/quote-requests", json=body, headers=headers)
    second = client.post("/api/v1/public/quote-requests", json=body, headers=headers)
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    assert "Pessoa Fictícia" not in first.text and "pessoa@example.test" not in first.text
    assert "Pessoa Fictícia" not in caplog.text
    assert "pessoa@example.test" not in caplog.text
    with get_session_factory()() as session:
        assert len(session.scalars(select(SalesLead)).all()) == 1
        lead = session.scalar(select(SalesLead))
        assert lead and lead.privacy_notice_version == "test-v1" and lead.consented_at
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "sales_lead.public_created")
        )
        assert audit and "pessoa@example.test" not in str(audit.details)
    no_consent = client.post(
        "/api/v1/public/quote-requests",
        json={**body, "privacy_consent": False},
        headers={"Idempotency-Key": "quote-test-key-0002"},
    )
    assert no_consent.status_code == 422


def test_public_quote_honeypot_is_not_saved_and_rate_limit_applies(client, monkeypatch):
    create_identity(slug="devmarkia-test", email="owner@example.test", role=Role.AGENCY_ADMIN)
    from growthos.config import get_settings
    from growthos.main import app

    monkeypatch.setitem(
        app.dependency_overrides, get_settings, lambda: enabled_quote_settings(attempts=1)
    )
    reset_login_rate_limiter()
    base = {
        "name": "Pessoa Fictícia",
        "goal": "Landing page",
        "email": "pessoa@example.test",
        "privacy_consent": True,
    }
    bot = client.post(
        "/api/v1/public/quote-requests",
        json={**base, "honeypot": "preenchido"},
        headers={"Idempotency-Key": "quote-bot-test-0001"},
    )
    assert bot.status_code == 202
    with get_session_factory()() as session:
        assert session.scalar(select(SalesLead.id)) is None
    reset_login_rate_limiter()
    first = client.post(
        "/api/v1/public/quote-requests",
        json=base,
        headers={"Idempotency-Key": "quote-rate-test-0001"},
    )
    second = client.post(
        "/api/v1/public/quote-requests",
        json=base,
        headers={"Idempotency-Key": "quote-rate-test-0002"},
    )
    assert first.status_code == 202
    assert second.status_code == 429 and second.headers.get("Retry-After")


def test_internal_pipeline_is_tenant_scoped_and_proposal_is_not_sent(client):
    owner = create_identity(slug="sales-owner", email="owner@example.test", role=Role.AGENCY_ADMIN)
    other = create_identity(slug="sales-other", email="other@example.test", role=Role.AGENCY_ADMIN)
    csrf = login(client, owner)
    created = client.post(
        "/api/v1/sales/leads",
        headers=csrf_headers(csrf),
        json={
            "name": "Lead Exemplo",
            "company": "Negócio Teste",
            "email": "lead@example.test",
            "goal": "Landing page comercial para divulgar meu serviço",
        },
    )
    assert created.status_code == 201, created.text
    lead_id = created.json()["id"]
    login(client, other)
    assert (
        client.get(
            f"/api/v1/sales/leads/{lead_id}/briefing",
            headers={"X-Organization-ID": str(other.organization_id)},
        ).status_code
        == 404
    )
    # This test client switches identity via cookies; re-login as the owning tenant.
    csrf = login(client, owner)
    for stage in ("CONTACT_PENDING", "BRIEFING"):
        response = client.patch(
            f"/api/v1/sales/leads/{lead_id}/stage",
            headers=csrf_headers(csrf),
            json={"stage": stage},
        )
        assert response.status_code == 200, response.text
    briefing = client.get(f"/api/v1/sales/leads/{lead_id}/briefing")
    assert briefing.status_code == 200 and briefing.json()["ai_used"] is False
    assert briefing.json()["service_classification"] == "IN_SCOPE_LANDING_PAGE"
    proposal = client.post(
        f"/api/v1/sales/leads/{lead_id}/proposal-draft", headers=csrf_headers(csrf)
    )
    assert proposal.status_code == 200 and proposal.json()["status"] == "DRAFT_NOT_SENT"
    assert proposal.json()["ai_used"] is False
    assert "R$ 1.690" in proposal.json()["body"]
    assert "Nada foi enviado" in proposal.json()["body"]
    task = client.post(
        f"/api/v1/sales/leads/{lead_id}/tasks",
        headers=csrf_headers(csrf),
        json={"title": "Confirmar materiais aprovados", "notes": "Somente exercício fictício"},
    )
    assert task.status_code == 201
    listed_tasks = client.get(f"/api/v1/sales/leads/{lead_id}/tasks")
    assert listed_tasks.status_code == 200
    assert listed_tasks.json()[0]["title"] == "Confirmar materiais aprovados"
    assert (
        client.patch(
            f"/api/v1/sales/leads/{lead_id}/stage",
            headers=csrf_headers(csrf),
            json={"stage": "CONTRACTED"},
        ).status_code
        == 409
    )
    for stage in (
        "PROPOSAL_SENT",
        "NEGOTIATION",
        "CONTRACTED",
        "IN_PRODUCTION",
        "DELIVERED",
        "AFTER_SALES",
    ):
        response = client.patch(
            f"/api/v1/sales/leads/{lead_id}/stage",
            headers=csrf_headers(csrf),
            json={"stage": stage},
        )
        assert response.status_code == 200, response.text
    client.cookies.clear()
    assert client.get("/api/v1/sales/leads").status_code == 401
    customer = create_identity(
        slug="sales-customer",
        email="customer@example.test",
        role=Role.CLIENT_OWNER,
        business_name="Empresa Cliente",
    )
    login(client, customer)
    assert client.get("/api/v1/sales/leads").status_code == 403


def test_sales_lead_retention_is_tenant_scoped_and_dry_run_first(client):
    identity = create_identity(
        slug="retention-sales", email="admin@example.test", role=Role.AGENCY_ADMIN
    )
    csrf = login(client, identity)
    with get_session_factory()() as session:
        session.add(
            RetentionPolicy(
                organization_id=identity.organization_id,
                resource_type="sales_leads",
                retention_days=30,
                legal_hold=False,
                justification="Prazo interno testado",
                updated_by_user_id=identity.user_id,
            )
        )
        old = SalesLead(
            organization_id=identity.organization_id,
            source="TEST",
            stage="NEW_LEAD",
            name="Teste",
            goal="teste",
            created_at=datetime.now(UTC) - timedelta(days=40),
        )
        session.add(old)
        session.commit()
        lead_id = old.id
    dry = client.post(
        "/api/v1/privacy/admin/retention/run",
        headers=csrf_headers(csrf),
        json={"resource_type": "sales_leads", "dry_run": True},
    )
    assert dry.status_code == 200 and dry.json()["affected_count"] == 1
    with get_session_factory()() as session:
        assert session.get(SalesLead, lead_id) is not None
    execute = client.post(
        "/api/v1/privacy/admin/retention/run",
        headers=csrf_headers(csrf),
        json={"resource_type": "sales_leads", "dry_run": False},
    )
    assert execute.status_code == 200 and execute.json()["affected_count"] == 1
    with get_session_factory()() as session:
        assert session.get(SalesLead, lead_id) is None
