from collections.abc import Generator
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from growthos.api.routes import auth, catalogs
from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import AuditLog, BrandProfile
from growthos.models.catalog import Service, VisualPreset
from tests.conftest import Identity, add_user_to_identity, create_identity, csrf_headers, login


@pytest.fixture
def catalog_client() -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(catalogs.router, prefix="/api/v1")
    with TestClient(app) as test_client:
        yield test_client


def _create_brand(identity: Identity, *, name: str = "Clínica Demo") -> None:
    assert identity.business_id is not None
    with get_session_factory()() as session:
        session.add(
            BrandProfile(
                organization_id=identity.organization_id,
                business_id=identity.business_id,
                brand_name=name,
                audience="Tutores responsáveis",
                tone_of_voice="acolhedor e responsável",
                primary_colors=["#14532D", "#F7F4EA"],
            )
        )
        session.commit()


def _preset_payload() -> dict[str, Any]:
    return {
        "name": "Educativo",
        "objective": "Explicar prevenção com clareza",
        "format": "FEED",
        "aspect_ratio": "1:1",
        "creation_mode": "HYBRID",
        "color_palette": ["#14532D", "#F7F4EA"],
        "fonts": ["Inter", "Merriweather"],
        "logo_position": "inferior direito",
        "logo_scale_percent": 18,
        "safe_margins": {"top": 8, "right": 8, "bottom": 10, "left": 8},
        "background_style": "consultório claro e organizado",
        "photographic_style": "fotografia documental acolhedora",
        "realism_level": "alto",
        "lighting": "luz natural suave",
        "composition": "animal e tutor em plano médio",
        "max_text_characters": 90,
        "text_rules": ["uma mensagem por peça", "alto contraste"],
        "base_prompt": "cena veterinária responsável e sem dramatização",
        "negative_prompt": "procedimentos invasivos",
        "allowed_elements": ["animais tranquilos", "equipe acolhedora"],
        "forbidden_elements": ["ferimentos", "promessas terapêuticas"],
        "visual_signature": "formas orgânicas verdes",
        "default_cta": "Converse com a equipe.",
    }


def test_catalog_crud_is_real_audited_and_archived(catalog_client: TestClient) -> None:
    identity = create_identity(
        slug="catalog-admin",
        email="catalog-admin@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica Catálogo",
    )
    assert identity.business_id is not None
    headers = csrf_headers(login(catalog_client, identity))
    base = f"/api/v1/businesses/{identity.business_id}"

    service = catalog_client.post(
        f"{base}/services",
        headers=headers,
        json={
            "name": "Consulta preventiva",
            "description": "Atendimento fictício para demonstração.",
            "category": "Consultas",
            "warnings": ["Não prometer resultado clínico"],
        },
    )
    assert service.status_code == 201, service.text
    service_id = service.json()["id"]
    assert catalog_client.get(f"{base}/services/{service_id}").status_code == 200

    updated = catalog_client.patch(
        f"{base}/services/{service_id}",
        headers=headers,
        json={"description": "Descrição revisada e persistida."},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["description"] == "Descrição revisada e persistida."

    audience = catalog_client.post(
        f"{base}/audiences",
        headers=headers,
        json={
            "name": "Tutores de primeira viagem",
            "description": "Público fictício.",
            "needs": ["informação clara"],
            "objections": ["receio de custos inesperados"],
            "location": "Região da clínica",
        },
    )
    assert audience.status_code == 201, audience.text
    assert len(catalog_client.get(f"{base}/audiences").json()) == 1

    objective = catalog_client.post(
        f"{base}/objectives",
        headers=headers,
        json={
            "name": "Educação preventiva",
            "description": "Aumentar a clareza do conteúdo.",
            "planned_indicators": ["conteúdos aprovados"],
        },
    )
    assert objective.status_code == 201, objective.text
    assert len(catalog_client.get(f"{base}/objectives").json()) == 1

    archived = catalog_client.delete(f"{base}/services/{service_id}", headers=headers)
    assert archived.status_code == 204, archived.text
    assert catalog_client.get(f"{base}/services/{service_id}").status_code == 404
    assert catalog_client.get(f"{base}/services").json() == []

    with get_session_factory()() as session:
        stored = session.scalar(select(Service).where(Service.id == UUID(service_id)))
        assert stored is not None
        assert stored.is_active is False
        assert stored.archived_at is not None
        actions = set(
            session.scalars(
                select(AuditLog.action).where(
                    AuditLog.organization_id == identity.organization_id,
                    AuditLog.business_id == identity.business_id,
                )
            ).all()
        )
    assert {
        "service.created",
        "service.updated",
        "service.archived",
        "audience_segment.created",
        "marketing_objective.created",
    }.issubset(actions)


def test_catalog_capabilities_and_tenant_scope_are_enforced(catalog_client: TestClient) -> None:
    first = create_identity(
        slug="catalog-first",
        email="catalog-first@example.com",
        role=Role.STRATEGIST,
        business_name="Clínica Primeira",
    )
    second = create_identity(
        slug="catalog-second",
        email="catalog-second@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica Segunda",
    )
    assert first.business_id is not None
    assert second.business_id is not None

    strategist_headers = csrf_headers(login(catalog_client, first))
    created = catalog_client.post(
        f"/api/v1/businesses/{first.business_id}/services",
        headers=strategist_headers,
        json={"name": "Serviço autorizado"},
    )
    assert created.status_code == 201, created.text

    viewer = add_user_to_identity(
        first,
        email="catalog-viewer@example.com",
        role=Role.VIEWER,
    )
    viewer_headers = csrf_headers(login(catalog_client, viewer))
    own_list = catalog_client.get(f"/api/v1/businesses/{first.business_id}/services")
    assert own_list.status_code == 200
    forbidden = catalog_client.post(
        f"/api/v1/businesses/{first.business_id}/services",
        headers=viewer_headers,
        json={"name": "Não permitido"},
    )
    assert forbidden.status_code == 403

    login(catalog_client, second)
    cross_tenant = catalog_client.get(f"/api/v1/businesses/{first.business_id}/services")
    assert cross_tenant.status_code == 404
    assert str(first.business_id) not in cross_tenant.text


def test_visual_preset_and_mock_prompt_use_scoped_persisted_brand(
    catalog_client: TestClient,
) -> None:
    identity = create_identity(
        slug="preset-admin",
        email="preset-admin@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica Preset",
    )
    assert identity.business_id is not None
    _create_brand(identity, name="Clínica Preset")
    headers = csrf_headers(login(catalog_client, identity))
    base = f"/api/v1/businesses/{identity.business_id}/visual-presets"

    created = catalog_client.post(base, headers=headers, json=_preset_payload())
    assert created.status_code == 201, created.text
    preset = created.json()
    preset_id = preset["id"]
    assert preset["version"] == 1
    assert preset["safe_margins"]["bottom"] == 10
    assert preset["forbidden_elements"] == ["ferimentos", "promessas terapêuticas"]

    changed = catalog_client.patch(
        f"{base}/{preset_id}",
        headers=headers,
        json={"background_style": "ambiente externo claro"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["version"] == 2

    prompt_input = {
        "business_id": str(identity.business_id),
        "preset_id": preset_id,
        "objective": "Explicar cuidados preventivos",
    }
    first = catalog_client.post(
        "/api/v1/visual-prompts/generate",
        headers=headers,
        json=prompt_input,
    )
    second = catalog_client.post(
        "/api/v1/visual-prompts/generate",
        headers=headers,
        json=prompt_input,
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json() == second.json()
    assert first.json()["provider_name"] == "mock"
    assert "Clínica Preset" in first.json()["prompt"]
    assert "Não inserir texto" in first.json()["prompt"]
    assert "promessas terapêuticas" in first.json()["negative_prompt"]

    with get_session_factory()() as session:
        stored = session.scalar(select(VisualPreset).where(VisualPreset.id == UUID(preset_id)))
        assert stored is not None
        assert stored.version == 2
        prompt_logs = list(
            session.scalars(
                select(AuditLog).where(
                    AuditLog.organization_id == identity.organization_id,
                    AuditLog.action == "visual_prompt.generated",
                )
            ).all()
        )
    assert len(prompt_logs) == 2
    assert all("prompt" not in entry.details for entry in prompt_logs)


def test_preset_requires_brand_and_prompt_rejects_cross_tenant_ids(
    catalog_client: TestClient,
) -> None:
    first = create_identity(
        slug="preset-first",
        email="preset-first@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica Sem Marca",
    )
    second = create_identity(
        slug="preset-second",
        email="preset-second@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica Com Marca",
    )
    assert first.business_id is not None
    assert second.business_id is not None

    first_headers = csrf_headers(login(catalog_client, first))
    missing_brand = catalog_client.post(
        f"/api/v1/businesses/{first.business_id}/visual-presets",
        headers=first_headers,
        json=_preset_payload(),
    )
    assert missing_brand.status_code == 409

    _create_brand(second)
    second_headers = csrf_headers(login(catalog_client, second))
    created = catalog_client.post(
        f"/api/v1/businesses/{second.business_id}/visual-presets",
        headers=second_headers,
        json=_preset_payload(),
    )
    assert created.status_code == 201, created.text

    first_headers = csrf_headers(login(catalog_client, first))
    cross_tenant = catalog_client.post(
        "/api/v1/visual-prompts/generate",
        headers=first_headers,
        json={
            "business_id": str(second.business_id),
            "preset_id": created.json()["id"],
            "objective": "Tentar acessar outro tenant",
        },
    )
    assert cross_tenant.status_code == 404
    assert created.json()["id"] not in cross_tenant.text
