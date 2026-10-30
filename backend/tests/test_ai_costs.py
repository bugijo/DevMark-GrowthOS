from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import AIGeneration, AIGenerationAttempt, AIUsageDaily
from growthos.services.ai_providers import AIProviderError, ProviderRequest, ProviderResult
from tests.conftest import create_identity, csrf_headers, login


class FailingProvider:
    name = "failed_provider"
    model = "failed-model"

    def generate(self, request: ProviderRequest) -> ProviderResult:
        del request
        raise AIProviderError("UNAVAILABLE")


class CostProvider:
    name = "openrouter"
    model = "provider/free-model:free"

    def __init__(self, cost: Decimal | None, status: str = "CONFIRMED") -> None:
        self.cost = cost
        self.status = status

    def generate(self, request: ProviderRequest) -> ProviderResult:
        return ProviderResult(
            alternatives=[{"title": "Ideia com custo", "caption": "Texto"}] * request.alternatives,
            provider=self.name,
            model=self.model,
            duration_ms=3,
            input_tokens=11,
            output_tokens=7,
            cost_usd=self.cost,
            cost_status=self.status,
            cost_origin="PROVIDER_USAGE_COST" if self.cost is not None else None,
        )


def test_cost_is_persisted_once_across_generation_attempt_usage_export_and_report(
    client: TestClient, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    identity = create_identity(
        slug="ai-cost",
        email="ai-cost@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica",
    )
    assert identity.business_id is not None
    monkeypatch.setattr(
        "growthos.services.growth_agent._providers",
        lambda settings: [FailingProvider(), CostProvider(Decimal("0.00012000"))],
    )
    csrf = login(client, identity)
    response = client.post(
        f"/api/v1/businesses/{identity.business_id}/ai/generations",
        headers=csrf_headers(csrf),
        json={"task": "CONTENT_IDEAS", "alternatives": 1},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["cost_usd"] == "0.00012000"
    assert body["cost_status"] == "CONFIRMED"
    assert body["cost_currency"] == "USD"
    assert body["used_fallback"] is True

    with get_session_factory()() as session:
        generation = session.get(AIGeneration, UUID(body["id"]))
        assert generation is not None and generation.cost_usd == Decimal("0.00012000")
        attempts = session.scalars(
            select(AIGenerationAttempt)
            .where(AIGenerationAttempt.generation_id == generation.id)
            .order_by(AIGenerationAttempt.created_at)
        ).all()
        assert [item.cost_status for item in attempts] == ["UNKNOWN", "CONFIRMED"]
        usage = session.scalar(
            select(AIUsageDaily).where(AIUsageDaily.organization_id == identity.organization_id)
        )
        assert usage is not None
        assert usage.confirmed_cost_usd == Decimal("0.00012000")
        assert usage.generation_count == 1

    exported = client.get("/api/v1/privacy/export").json()["ai_generations"][0]
    assert exported["cost_usd"] == "0.00012000"
    report = client.get(
        f"/api/v1/businesses/{identity.business_id}/reports/period",
        params={"starts_on": "2020-01-01", "ends_on": "2030-01-01"},
    )
    assert report.status_code == 422  # limite de período permanece protegido
    today = body["created_at"][:10]
    report = client.get(
        f"/api/v1/businesses/{identity.business_id}/reports/period",
        params={"starts_on": today, "ends_on": today},
    )
    assert report.status_code == 200
    assert report.json()["ai_confirmed_cost_usd"] == "0.00012000"
    assert report.json()["ai_unknown_cost_count"] == 0


def test_regeneration_is_accounted_separately_and_unknown_cost_stays_unknown(
    client: TestClient, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    identity = create_identity(
        slug="ai-cost-regen",
        email="ai-cost-regen@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica",
    )
    assert identity.business_id is not None
    monkeypatch.setattr(
        "growthos.services.growth_agent._providers",
        lambda settings: [CostProvider(None, "UNKNOWN")],
    )
    csrf = login(client, identity)
    first = client.post(
        f"/api/v1/businesses/{identity.business_id}/ai/generations",
        headers=csrf_headers(csrf),
        json={"task": "TITLE", "alternatives": 1},
    )
    assert first.status_code == 201
    regenerated = client.post(
        f"/api/v1/ai/generations/{first.json()['id']}/regenerate",
        headers=csrf_headers(csrf),
    )
    assert regenerated.status_code == 201
    assert regenerated.json()["cost_usd"] is None
    assert regenerated.json()["cost_status"] == "UNKNOWN"
    with get_session_factory()() as session:
        usage = session.scalar(
            select(AIUsageDaily).where(AIUsageDaily.organization_id == identity.organization_id)
        )
        assert usage is not None
        assert usage.generation_count == 2
        assert usage.unknown_cost_count == 2
        assert usage.confirmed_cost_usd == Decimal("0")
