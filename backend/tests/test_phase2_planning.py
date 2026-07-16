from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import BrandProfile, ContentPlan, Job
from tests.conftest import add_user_to_identity, create_identity, csrf_headers, login


def _brand(organization_id: object, business_id: object) -> None:
    with get_session_factory()() as session:
        session.add(
            BrandProfile(
                organization_id=organization_id,
                business_id=business_id,
                brand_name="Clínica Planejada",
                audience="Tutores responsáveis",
                tone_of_voice="acolhedor e responsável",
                primary_colors=["#146B5F"],
                differentiators=["atendimento humanizado"],
            )
        )
        session.commit()


def _prepare_strategy(client: TestClient) -> tuple[object, dict[str, str], dict[str, object]]:
    admin = create_identity(
        slug="planning",
        email="planning-admin@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica Planejada",
    )
    assert admin.business_id is not None
    reviewer = add_user_to_identity(
        admin,
        email="planning-reviewer@example.com",
        role=Role.CLIENT_REVIEWER,
        password="reviewer-password-123",
    )
    _brand(admin.organization_id, admin.business_id)
    headers = csrf_headers(login(client, admin))
    base = f"/api/v1/businesses/{admin.business_id}"
    service = client.post(
        f"{base}/services",
        json={"name": "Consulta preventiva"},
        headers=headers,
    ).json()
    audience = client.post(
        f"{base}/audiences",
        json={"name": "Tutores de primeira viagem"},
        headers=headers,
    ).json()
    objective = client.post(
        f"{base}/objectives",
        json={"name": "Educação preventiva"},
        headers=headers,
    ).json()
    created = client.post(
        f"{base}/strategies",
        json={
            "name": "Estratégia agosto",
            "starts_on": "2026-08-01",
            "ends_on": "2026-08-31",
            "objective": "Educar sobre prevenção responsável",
            "service_ids": [service["id"]],
            "audience_ids": [audience["id"]],
            "marketing_objective_ids": [objective["id"]],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    return reviewer, headers, created.json()


def test_strategy_approval_plan_and_monthly_weekly_calendar(client: TestClient) -> None:
    reviewer, headers, strategy = _prepare_strategy(client)
    strategy_id = strategy["id"]
    assert strategy["status"] == "DRAFT"
    assert strategy["current_version"]["version_number"] == 1
    assert strategy["current_version"]["provider_name"] == "mock"
    assert strategy["current_version"]["service_snapshots"][0]["name"] == ("Consulta preventiva")
    assert (
        client.post(
            f"/api/v1/strategies/{strategy_id}/submit-internal",
            headers=headers,
        ).json()["status"]
        == "INTERNAL_REVIEW"
    )
    sent = client.post(
        f"/api/v1/strategies/{strategy_id}/send-to-client",
        headers=headers,
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "CLIENT_REVIEW"

    reviewer_client = TestClient(client.app)
    reviewer_csrf = login(reviewer_client, reviewer)
    visible = reviewer_client.get(f"/api/v1/businesses/{reviewer.business_id}/strategies")
    assert [item["id"] for item in visible.json()] == [strategy_id]
    approved = reviewer_client.post(
        f"/api/v1/strategies/{strategy_id}/decision",
        json={"decision": "APPROVE", "comment": "Direção aprovada"},
        headers=csrf_headers(reviewer_csrf),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"

    plan = client.post(
        f"/api/v1/businesses/{reviewer.business_id}/plans",
        json={
            "strategy_id": strategy_id,
            "name": "Calendário agosto",
            "starts_on": "2026-08-01",
            "ends_on": "2026-08-31",
            "frequency": "SEMANAL",
        },
        headers=headers,
    )
    assert plan.status_code == 201, plan.text
    generated = client.post(
        f"/api/v1/plans/{plan.json()['id']}/generate-mock",
        headers=headers,
    )
    assert generated.status_code == 200, generated.text
    assert len(generated.json()) == 5
    assert all(item["status"] == "GENERATED" for item in generated.json())

    monthly = client.get(
        f"/api/v1/businesses/{reviewer.business_id}/calendar",
        params={"starts_on": "2026-08-01", "ends_on": "2026-08-31"},
    )
    weekly = client.get(
        f"/api/v1/businesses/{reviewer.business_id}/calendar",
        params={"starts_on": "2026-08-01", "ends_on": "2026-08-07"},
    )
    assert len(monthly.json()) == 5
    assert len(weekly.json()) == 1

    actions = {item["action"] for item in client.get("/api/v1/audit-logs").json()}
    assert {
        "strategy.created",
        "strategy.sent_to_client",
        "strategy.approved_by_client",
        "content_plan.created",
        "calendar.generated_mock",
    } <= actions
    with get_session_factory()() as session:
        jobs = session.scalars(select(Job).where(Job.type == "notification.email.smtp")).all()
        assert len(jobs) == 1
        assert "token" not in str(jobs[0].payload).casefold()


def test_strategy_change_request_requires_new_version_and_is_tenant_isolated(
    client: TestClient,
) -> None:
    reviewer, headers, strategy = _prepare_strategy(client)
    strategy_id = strategy["id"]
    client.post(f"/api/v1/strategies/{strategy_id}/submit-internal", headers=headers)
    client.post(f"/api/v1/strategies/{strategy_id}/send-to-client", headers=headers)
    reviewer_client = TestClient(client.app)
    reviewer_csrf = login(reviewer_client, reviewer)
    changes = reviewer_client.post(
        f"/api/v1/strategies/{strategy_id}/decision",
        json={"decision": "CHANGES_REQUESTED", "comment": "Detalhar o público"},
        headers=csrf_headers(reviewer_csrf),
    )
    assert changes.status_code == 200, changes.text
    assert changes.json()["status"] == "DRAFT"

    revised = client.post(
        f"/api/v1/strategies/{strategy_id}/versions",
        json={
            "objective": "Educar tutores novos sobre prevenção responsável",
            "audience_ids": [strategy["current_version"]["audience_snapshots"][0]["id"]],
        },
        headers=headers,
    )
    assert revised.status_code == 200, revised.text
    assert revised.json()["current_version"]["version_number"] == 2
    assert revised.json()["decision_comment"] is None

    other_client = TestClient(client.app)
    other = create_identity(
        slug="planning-other",
        email="planning-other@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Outra clínica",
    )
    login(other_client, other)
    assert (
        other_client.get(f"/api/v1/businesses/{reviewer.business_id}/strategies").status_code == 404
    )


def test_calendar_generation_rejects_strategy_version_from_another_tenant(
    client: TestClient,
) -> None:
    reviewer, headers, strategy = _prepare_strategy(client)
    strategy_id = strategy["id"]
    client.post(f"/api/v1/strategies/{strategy_id}/submit-internal", headers=headers)
    client.post(f"/api/v1/strategies/{strategy_id}/send-to-client", headers=headers)
    reviewer_client = TestClient(client.app)
    reviewer_csrf = login(reviewer_client, reviewer)
    approved = reviewer_client.post(
        f"/api/v1/strategies/{strategy_id}/decision",
        json={"decision": "APPROVE"},
        headers=csrf_headers(reviewer_csrf),
    )
    assert approved.status_code == 200, approved.text
    plan = client.post(
        f"/api/v1/businesses/{reviewer.business_id}/plans",
        json={
            "strategy_id": strategy_id,
            "name": "Plano com vínculo adulterado",
            "starts_on": "2026-08-01",
            "ends_on": "2026-08-31",
        },
        headers=headers,
    )
    assert plan.status_code == 201, plan.text

    other_client = TestClient(client.app)
    other = create_identity(
        slug="planning-version-other",
        email="planning-version-other@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica de outro tenant",
    )
    assert other.business_id is not None
    _brand(other.organization_id, other.business_id)
    other_headers = csrf_headers(login(other_client, other))
    other_strategy = other_client.post(
        f"/api/v1/businesses/{other.business_id}/strategies",
        json={
            "name": "Estratégia externa",
            "starts_on": "2026-08-01",
            "ends_on": "2026-08-31",
            "objective": "Objetivo que não pode atravessar tenants",
        },
        headers=other_headers,
    )
    assert other_strategy.status_code == 201, other_strategy.text

    with get_session_factory()() as session:
        stored_plan = session.get(ContentPlan, UUID(plan.json()["id"]))
        assert stored_plan is not None
        stored_plan.strategy_version_id = UUID(other_strategy.json()["current_version"]["id"])
        session.commit()

    generated = client.post(
        f"/api/v1/plans/{plan.json()['id']}/generate-mock",
        headers=headers,
    )
    assert generated.status_code == 409, generated.text
    assert generated.json()["detail"] == "Versão da estratégia indisponível"
