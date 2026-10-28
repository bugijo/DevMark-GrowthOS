from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from growthos.config import get_settings
from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.integration_tokens_cli import main as token_cli
from growthos.models import AuditLog, IntegrationToken, Organization
from growthos.services import integrations
from tests.conftest import create_identity, csrf_headers, login
from tests.test_landing import VILLA_PET_PAGE


def _issue(organization_id, *, scopes=None, ttl=timedelta(days=1)) -> str:
    with get_session_factory()() as session:
        organization = session.get(Organization, organization_id)
        _, value = integrations.issue_integration_token(
            session,
            get_settings().effective_token_secret_key,
            organization,
            label="hermes-test",
            scopes=[integrations.LEADS_READ] if scopes is None else scopes,
            ttl=ttl,
        )
    return value


def _setup_with_lead(client, slug: str):
    owner = create_identity(
        slug=slug, email=f"{slug}@example.test", role=Role.AGENCY_ADMIN, business_name="Villa Pet"
    )
    csrf = login(client, owner)
    page = {**VILLA_PET_PAGE, "slug": f"{slug}-page"}
    client.put(
        f"/api/v1/businesses/{owner.business_id}/landing-page",
        headers=csrf_headers(csrf),
        json=page,
    )
    client.post(
        f"/api/v1/businesses/{owner.business_id}/leads",
        headers=csrf_headers(csrf),
        json={
            "source": "INDICACAO",
            "service_requested": "Banho",
            "price_item_label": "Grande",
            "preferred_period": "Sábado",
            "notes": "Observação interna que não deve sair pela integração",
        },
    )
    client.cookies.clear()
    return owner


def test_read_only_token_reads_summary_and_leads_without_notes(client) -> None:
    owner = _setup_with_lead(client, "integration-read")
    token = _issue(owner.organization_id)
    auth = {"Authorization": f"Bearer {token}"}

    listed = client.get("/api/v1/integrations/v1/businesses", headers=auth)
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["name"] == "Villa Pet"
    assert listed.json()[0]["summary"]["total"] == 1

    summary = client.get(
        f"/api/v1/integrations/v1/businesses/{owner.business_id}/leads/summary", headers=auth
    )
    assert summary.status_code == 200 and summary.json()["open_without_next_action"] == 1

    leads = client.get(
        f"/api/v1/integrations/v1/businesses/{owner.business_id}/leads", headers=auth
    )
    assert leads.status_code == 200
    lead = leads.json()[0]
    assert lead["reference_price_cents"] == 9500 and lead["is_demo"] is True
    assert "notes" not in lead

    with get_session_factory()() as session:
        reads = session.scalars(
            select(AuditLog.details).where(AuditLog.action == "integration.read")
        ).all()
        assert {d["resource"] for d in reads} == {"businesses", "leads.summary", "leads"}
        row = session.scalar(select(IntegrationToken))
        assert row is not None and row.last_used_at is not None
        assert token not in row.token_hash


def test_integration_rejects_sessions_writes_bad_tokens_and_other_tenants(client) -> None:
    owner = _setup_with_lead(client, "integration-owner")
    other = _setup_with_lead(client, "integration-other")
    token = _issue(owner.organization_id)
    auth = {"Authorization": f"Bearer {token}"}
    leads_url = f"/api/v1/integrations/v1/businesses/{owner.business_id}/leads"

    assert client.get(leads_url).status_code == 401
    assert (
        client.get(leads_url, headers={"Authorization": "Bearer nao-e-um-token"}).status_code == 401
    )
    assert (
        client.get(leads_url, headers={"Authorization": f"Bearer {token[:-1]}x"}).status_code == 401
    )
    # Uma sessão humana não abre a API de integração.
    login(client, owner)
    assert client.get(leads_url).status_code == 401
    client.cookies.clear()

    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)(leads_url, headers=auth).status_code == 405
    other_url = f"/api/v1/integrations/v1/businesses/{other.business_id}/leads"
    assert client.get(other_url, headers=auth).status_code == 404


def test_expired_and_revoked_tokens_are_refused(client) -> None:
    owner = _setup_with_lead(client, "integration-expiry")
    token = _issue(owner.organization_id)
    url = "/api/v1/integrations/v1/businesses"
    auth = {"Authorization": f"Bearer {token}"}
    assert client.get(url, headers=auth).status_code == 200

    with get_session_factory()() as session:
        row = session.scalar(select(IntegrationToken))
        assert row is not None
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
        token_id = row.id
    assert client.get(url, headers=auth).status_code == 401

    with get_session_factory()() as session:
        row = session.get(IntegrationToken, token_id)
        row.expires_at = datetime.now(UTC) + timedelta(days=1)
        session.commit()
        integrations.revoke_integration_token(session, token_id)
    assert client.get(url, headers=auth).status_code == 401


def test_issue_validates_scopes_and_ttl(client) -> None:
    owner = create_identity(
        slug="integration-scope", email="scope@example.test", role=Role.AGENCY_ADMIN
    )
    for bad in ({"scopes": ["leads:write"]}, {"scopes": []}, {"ttl": timedelta(days=91)}):
        try:
            _issue(owner.organization_id, **bad)
        except ValueError:
            continue
        raise AssertionError(f"deveria recusar {bad}")


def test_cli_prints_only_the_token_on_stdout(client, capsys) -> None:
    owner = create_identity(
        slug="integration-cli", email="cli@example.test", role=Role.AGENCY_ADMIN
    )
    with get_session_factory()() as session:
        slug = session.get(Organization, owner.organization_id).slug
    assert token_cli(["issue", "--org", slug, "--label", "hermes", "--days", "7"]) == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().splitlines()
    assert len(lines) == 1 and "." in lines[0]
    assert "emitido" in captured.err and lines[0] not in captured.err
