from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from growthos.api.routes import comparisons as comparison_routes
from growthos.database import get_session_factory
from growthos.domain.enums import (
    ApprovalComponent,
    ApprovalStage,
    ApprovalStatus,
    ContentStatus,
    Role,
)
from growthos.domain.permissions import Capability
from growthos.models import (
    Approval,
    AuditLog,
    Business,
    ContentItem,
    ContentStrategy,
    ContentVersion,
    ContentVersionMedia,
    StrategyVersion,
)
from tests.conftest import (
    Identity,
    add_user_to_identity,
    create_identity,
    create_ready_media,
    login,
)


@dataclass(frozen=True)
class ComparisonFixture:
    admin: Identity
    reviewer: Identity
    content_id: UUID
    content_version_ids: tuple[UUID, UUID]
    content_media_ids: tuple[UUID, UUID]
    strategy_id: UUID
    strategy_version_ids: tuple[UUID, UUID]


def _create_fixture(slug: str) -> ComparisonFixture:
    admin = create_identity(
        slug=slug,
        email=f"{slug}-admin@example.com",
        role=Role.AGENCY_ADMIN,
        business_name=f"Clínica {slug}",
    )
    reviewer = add_user_to_identity(
        admin,
        email=f"{slug}-reviewer@example.com",
        role=Role.CLIENT_REVIEWER,
    )
    assert admin.business_id is not None
    media_one_id = create_ready_media(admin, display_name="versao-1.png")
    media_two_id = create_ready_media(admin, display_name="versao-2.png")
    first_created_at = datetime(2026, 7, 1, 12, tzinfo=UTC)
    second_created_at = datetime(2026, 7, 2, 12, tzinfo=UTC)
    decision_at = datetime(2026, 7, 3, 12, tzinfo=UTC)

    with get_session_factory()() as session:
        content = ContentItem(
            organization_id=admin.organization_id,
            business_id=admin.business_id,
            status=ContentStatus.CLIENT_REVIEW,
            created_by_user_id=admin.user_id,
        )
        session.add(content)
        session.flush()
        content_v1 = ContentVersion(
            organization_id=admin.organization_id,
            business_id=admin.business_id,
            content_item_id=content.id,
            version_number=1,
            title="Consulta preventiva",
            caption="Cuide hoje.",
            channel="INSTAGRAM",
            format="FEED",
            objective="Educar tutores",
            audience="Tutores responsáveis",
            cta="Agende uma conversa.",
            notes="nota-interna-nao-pode-sair",
            script="Mostre uma rotina preventiva.",
            visual_prompt="prompt-interno-nao-pode-sair",
            negative_prompt="negative-prompt-nao-pode-sair",
            brand_context_snapshot={"segredo_de_marca": "nao-expor"},
            visual_preset_snapshot={
                "id": "preset-v1",
                "name": "Acolhedor",
                "background_style": "consultório claro",
                "base_prompt": "base-prompt-nao-pode-sair",
                "negative_prompt": "preset-negative-nao-pode-sair",
                "prompt_provider_reference": "provider-reference-nao-pode-sair",
            },
            provider_name="mock-interno",
            created_by_user_id=admin.user_id,
            created_at=first_created_at,
        )
        content_v2 = ContentVersion(
            organization_id=admin.organization_id,
            business_id=admin.business_id,
            content_item_id=content.id,
            version_number=2,
            title="Consulta preventiva",
            caption="Prevenção começa com informação responsável.",
            channel="INSTAGRAM",
            format="FEED",
            objective="Educar tutores",
            audience="Tutores responsáveis",
            cta="Agende uma conversa.",
            notes="outra-nota-interna",
            script="Mostre uma rotina preventiva.",
            visual_prompt="outro-prompt-interno",
            negative_prompt="outro-negative-prompt",
            brand_context_snapshot={"segredo_de_marca": "continua-interno"},
            visual_preset_snapshot={
                "id": "preset-v2",
                "name": "Acolhedor atualizado",
                "background_style": "consultório com luz natural",
                "base_prompt": "base-prompt-v2-nao-pode-sair",
            },
            provider_name="mock-interno",
            created_by_user_id=admin.user_id,
            created_at=second_created_at,
        )
        session.add_all([content_v1, content_v2])
        session.flush()
        content.current_version_id = content_v2.id
        session.add_all(
            [
                ContentVersionMedia(
                    organization_id=admin.organization_id,
                    business_id=admin.business_id,
                    content_version_id=content_v1.id,
                    media_asset_id=media_one_id,
                    role="PRIMARY",
                    sort_order=0,
                    created_by_user_id=admin.user_id,
                    created_at=first_created_at,
                ),
                ContentVersionMedia(
                    organization_id=admin.organization_id,
                    business_id=admin.business_id,
                    content_version_id=content_v2.id,
                    media_asset_id=media_two_id,
                    role="PRIMARY",
                    sort_order=0,
                    created_by_user_id=admin.user_id,
                    created_at=second_created_at,
                ),
            ]
        )
        for component, comment in (
            (ApprovalComponent.TEXT, "Texto aprovado com responsabilidade."),
            (ApprovalComponent.IMAGE, "Imagem aprovada sem informação clínica."),
        ):
            session.add(
                Approval(
                    organization_id=admin.organization_id,
                    business_id=admin.business_id,
                    content_item_id=content.id,
                    content_version_id=content_v1.id,
                    stage=ApprovalStage.CLIENT,
                    component=component,
                    status=ApprovalStatus.APPROVED,
                    requested_by_user_id=admin.user_id,
                    decided_by_user_id=reviewer.user_id,
                    decision_comment=comment,
                    decided_at=decision_at,
                )
            )
            session.add(
                Approval(
                    organization_id=admin.organization_id,
                    business_id=admin.business_id,
                    content_item_id=content.id,
                    content_version_id=content_v2.id,
                    stage=ApprovalStage.CLIENT,
                    component=component,
                    status=ApprovalStatus.PENDING,
                    requested_by_user_id=admin.user_id,
                )
            )

        strategy = ContentStrategy(
            organization_id=admin.organization_id,
            business_id=admin.business_id,
            name="Estratégia mensal",
            starts_on=date(2026, 7, 1),
            ends_on=date(2026, 7, 31),
            status="APPROVED",
            created_by_user_id=admin.user_id,
            decided_by_user_id=reviewer.user_id,
            decided_at=decision_at,
            decision_comment="Estratégia aprovada para o mês.",
        )
        session.add(strategy)
        session.flush()
        strategy_v1 = StrategyVersion(
            organization_id=admin.organization_id,
            business_id=admin.business_id,
            content_strategy_id=strategy.id,
            version_number=1,
            objective="Informar sobre prevenção",
            positioning="Clínica próxima dos tutores",
            funnel=["DESCOBERTA"],
            channels=["INSTAGRAM"],
            pillars=["Prevenção"],
            planned_indicators=["conteúdos planejados"],
            service_snapshots=[{"id": "servico-1", "name": "Consulta", "internal": "nao-expor"}],
            audience_snapshots=[{"id": "publico-1", "name": "Tutores"}],
            objective_snapshots=[{"id": "objetivo-1", "name": "Educação"}],
            brand_context_snapshot={"segredo_de_marca": "nao-expor"},
            source="MOCK",
            provider_name="mock",
            provider_reference="strategy-provider-reference-nao-pode-sair",
            created_by_user_id=admin.user_id,
            created_at=first_created_at,
        )
        strategy_v2 = StrategyVersion(
            organization_id=admin.organization_id,
            business_id=admin.business_id,
            content_strategy_id=strategy.id,
            version_number=2,
            objective="Informar sobre prevenção e longevidade",
            positioning="Clínica próxima dos tutores",
            funnel=["DESCOBERTA"],
            channels=["INSTAGRAM"],
            pillars=["Prevenção", "Longevidade"],
            planned_indicators=["conteúdos planejados"],
            service_snapshots=[{"id": "servico-1", "name": "Consulta"}],
            audience_snapshots=[{"id": "publico-1", "name": "Tutores"}],
            objective_snapshots=[{"id": "objetivo-1", "name": "Educação"}],
            brand_context_snapshot={"segredo_de_marca": "continua-interno"},
            source="MOCK",
            provider_name="mock",
            provider_reference="strategy-provider-reference-v2-nao-pode-sair",
            created_by_user_id=admin.user_id,
            supersedes_version_id=strategy_v1.id,
            created_at=second_created_at,
        )
        session.add_all([strategy_v1, strategy_v2])
        session.flush()
        strategy.current_version_id = strategy_v2.id
        strategy.approved_version_id = strategy_v2.id
        session.add(
            AuditLog(
                organization_id=admin.organization_id,
                business_id=admin.business_id,
                actor_user_id=reviewer.user_id,
                action="strategy.approved_by_client",
                resource_type="content_strategy",
                resource_id=strategy.id,
                details={"version_id": str(strategy_v2.id)},
                created_at=decision_at,
            )
        )
        session.commit()
        return ComparisonFixture(
            admin=admin,
            reviewer=reviewer,
            content_id=content.id,
            content_version_ids=(content_v1.id, content_v2.id),
            content_media_ids=(media_one_id, media_two_id),
            strategy_id=strategy.id,
            strategy_version_ids=(strategy_v1.id, strategy_v2.id),
        )


def _comparison_params(version_ids: tuple[UUID, UUID]) -> dict[str, str]:
    return {
        "base_version_id": str(version_ids[0]),
        "target_version_id": str(version_ids[1]),
    }


def _create_other_business_resources(identity: Identity) -> tuple[UUID, UUID]:
    with get_session_factory()() as session:
        business = Business(
            organization_id=identity.organization_id,
            name="Empresa fora do escopo do cliente",
            segment="Veterinária",
        )
        session.add(business)
        session.flush()
        content = ContentItem(
            organization_id=identity.organization_id,
            business_id=business.id,
            status=ContentStatus.CLIENT_REVIEW,
            created_by_user_id=identity.user_id,
        )
        strategy = ContentStrategy(
            organization_id=identity.organization_id,
            business_id=business.id,
            name="Estratégia fora do escopo",
            starts_on=date(2026, 7, 1),
            ends_on=date(2026, 7, 31),
            status="APPROVED",
            created_by_user_id=identity.user_id,
        )
        session.add_all([content, strategy])
        session.flush()
        content_version = ContentVersion(
            organization_id=identity.organization_id,
            business_id=business.id,
            content_item_id=content.id,
            version_number=1,
            title="Conteúdo externo",
            caption="Não pode aparecer",
            channel="INSTAGRAM",
            format="FEED",
            objective="Isolamento",
            provider_name="mock",
            created_by_user_id=identity.user_id,
        )
        strategy_version = StrategyVersion(
            organization_id=identity.organization_id,
            business_id=business.id,
            content_strategy_id=strategy.id,
            version_number=1,
            objective="Não pode aparecer",
            source="MOCK",
            provider_name="mock",
            created_by_user_id=identity.user_id,
        )
        session.add_all([content_version, strategy_version])
        session.flush()
        content.current_version_id = content_version.id
        strategy.current_version_id = strategy_version.id
        strategy.approved_version_id = strategy_version.id
        session.commit()
        return content.id, strategy.id


def test_content_history_and_comparison_are_exact_and_sanitized(
    client: TestClient,
) -> None:
    fixture = _create_fixture("comparison-content")
    login(client, fixture.admin)

    history = client.get(f"/api/v1/contents/{fixture.content_id}/history")
    assert history.status_code == 200, history.text
    versions = history.json()["versions"]
    assert [version["version_number"] for version in versions] == [1, 2]
    assert [version["is_current"] for version in versions] == [False, True]
    assert [version["is_approved"] for version in versions] == [True, False]
    assert versions[0]["author"]["name"] == "User comparison-content"
    assert [decision["component"] for decision in versions[0]["decisions"]] == [
        "IMAGE",
        "TEXT",
    ]
    assert {decision["comment"] for decision in versions[0]["decisions"]} == {
        "Texto aprovado com responsabilidade.",
        "Imagem aprovada sem informação clínica.",
    }

    compared = client.get(
        f"/api/v1/contents/{fixture.content_id}/compare",
        params=_comparison_params(fixture.content_version_ids),
    )
    assert compared.status_code == 200, compared.text
    payload = compared.json()
    assert payload["base"]["id"] == str(fixture.content_version_ids[0])
    assert payload["target"]["id"] == str(fixture.content_version_ids[1])
    assert payload["base"]["visual"]["media_asset_ids"] == [str(fixture.content_media_ids[0])]
    assert payload["target"]["visual"]["media_asset_ids"] == [str(fixture.content_media_ids[1])]
    assert payload["changed_fields"] == [
        "text.caption",
        "visual.preset",
        "visual.media_asset_ids",
    ]
    serialized = compared.text.casefold()
    for internal_value in (
        "nota-interna",
        "prompt-interno",
        "negative-prompt",
        "base-prompt",
        "provider-reference",
        "segredo_de_marca",
        "mock-interno",
    ):
        assert internal_value not in serialized


def test_strategy_history_and_comparison_mark_the_approved_version(
    client: TestClient,
) -> None:
    fixture = _create_fixture("comparison-strategy")
    login(client, fixture.admin)

    history = client.get(f"/api/v1/strategies/{fixture.strategy_id}/history")
    assert history.status_code == 200, history.text
    payload = history.json()
    assert payload["current_version_id"] == str(fixture.strategy_version_ids[1])
    assert payload["approved_version_id"] == str(fixture.strategy_version_ids[1])
    assert [version["version_number"] for version in payload["versions"]] == [1, 2]
    assert [version["is_approved"] for version in payload["versions"]] == [False, True]
    decision = payload["versions"][1]["decisions"][0]
    assert decision["status"] == "APPROVED"
    assert decision["comment"] == "Estratégia aprovada para o mês."
    assert decision["decided_by"]["name"] == "Additional user"

    compared = client.get(
        f"/api/v1/strategies/{fixture.strategy_id}/compare",
        params=_comparison_params(fixture.strategy_version_ids),
    )
    assert compared.status_code == 200, compared.text
    comparison = compared.json()
    assert comparison["changed_fields"] == [
        "strategy.objective",
        "strategy.pillars",
    ]
    assert comparison["base"]["strategy"]["services"] == [{"id": "servico-1", "name": "Consulta"}]
    serialized = compared.text.casefold()
    assert "strategy-provider-reference" not in serialized
    assert "segredo_de_marca" not in serialized
    assert '"internal"' not in serialized


def test_comparisons_reject_wrong_versions_and_cross_tenant_access(
    client: TestClient,
) -> None:
    first = _create_fixture("comparison-first")
    second = _create_fixture("comparison-second")
    login(client, first.admin)

    wrong_content_version = client.get(
        f"/api/v1/contents/{first.content_id}/compare",
        params={
            "base_version_id": str(first.content_version_ids[0]),
            "target_version_id": str(second.content_version_ids[1]),
        },
    )
    assert wrong_content_version.status_code == 404
    wrong_strategy_version = client.get(
        f"/api/v1/strategies/{first.strategy_id}/compare",
        params={
            "base_version_id": str(first.strategy_version_ids[0]),
            "target_version_id": str(second.strategy_version_ids[1]),
        },
    )
    assert wrong_strategy_version.status_code == 404
    same_version = client.get(
        f"/api/v1/contents/{first.content_id}/compare",
        params={
            "base_version_id": str(first.content_version_ids[0]),
            "target_version_id": str(first.content_version_ids[0]),
        },
    )
    assert same_version.status_code == 422

    other_client = TestClient(client.app)
    login(other_client, second.admin)
    assert other_client.get(f"/api/v1/contents/{first.content_id}/history").status_code == 404
    assert other_client.get(f"/api/v1/strategies/{first.strategy_id}/history").status_code == 404


def test_client_comparisons_fail_closed_outside_its_business(
    client: TestClient,
) -> None:
    fixture = _create_fixture("comparison-business-scope")
    external_content_id, external_strategy_id = _create_other_business_resources(fixture.admin)
    login(client, fixture.reviewer)

    assert client.get(f"/api/v1/contents/{external_content_id}/history").status_code == 404
    assert client.get(f"/api/v1/strategies/{external_strategy_id}/history").status_code == 404
    assert client.get(f"/api/v1/contents/{fixture.content_id}/history").status_code == 200
    assert client.get(f"/api/v1/strategies/{fixture.strategy_id}/history").status_code == 200


@pytest.mark.parametrize(
    ("path_factory", "expected_capability"),
    [
        (
            lambda fixture: f"/api/v1/contents/{fixture.content_id}/history",
            Capability.CONTENT_VIEW,
        ),
        (
            lambda fixture: f"/api/v1/strategies/{fixture.strategy_id}/history",
            Capability.STRATEGY_VIEW,
        ),
    ],
)
def test_comparison_routes_enforce_capabilities(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path_factory: object,
    expected_capability: Capability,
) -> None:
    fixture = _create_fixture(f"comparison-rbac-{expected_capability.name.lower()}")
    login(client, fixture.admin)
    checked: list[Capability] = []

    def deny(_context: object, capability: Capability) -> None:
        checked.append(capability)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "negado pelo teste")

    monkeypatch.setattr(comparison_routes, "require_capability", deny)
    response = client.get(path_factory(fixture))  # type: ignore[operator]
    assert response.status_code == 403
    assert checked == [expected_capability]


def test_comparison_gets_do_not_mutate_versions_or_audit_log(client: TestClient) -> None:
    fixture = _create_fixture("comparison-immutable")
    login(client, fixture.admin)
    with get_session_factory()() as session:
        content_before = session.scalar(
            select(ContentVersion.caption).where(
                ContentVersion.id == fixture.content_version_ids[0]
            )
        )
        strategy_before = session.scalar(
            select(StrategyVersion.objective).where(
                StrategyVersion.id == fixture.strategy_version_ids[0]
            )
        )
        audit_count_before = session.scalar(select(func.count()).select_from(AuditLog))

    assert (
        client.get(
            f"/api/v1/contents/{fixture.content_id}/compare",
            params=_comparison_params(fixture.content_version_ids),
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/strategies/{fixture.strategy_id}/compare",
            params=_comparison_params(fixture.strategy_version_ids),
        ).status_code
        == 200
    )

    with get_session_factory()() as session:
        assert (
            session.scalar(
                select(ContentVersion.caption).where(
                    ContentVersion.id == fixture.content_version_ids[0]
                )
            )
            == content_before
        )
        assert (
            session.scalar(
                select(StrategyVersion.objective).where(
                    StrategyVersion.id == fixture.strategy_version_ids[0]
                )
            )
            == strategy_before
        )
        assert session.scalar(select(func.count()).select_from(AuditLog)) == audit_count_before
