from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import (
    AuditLog,
    BrandProfile,
    Business,
    BusinessOnboarding,
    Membership,
    Service,
    VisualPreset,
)
from tests.conftest import (
    Identity,
    add_user_to_identity,
    create_identity,
    create_ready_media,
    csrf_headers,
    login,
)


def _start(client: TestClient, identity: Identity, csrf: str) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/businesses/{identity.business_id}/onboarding",
        headers=csrf_headers(csrf),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _save(
    client: TestClient,
    identity: Identity,
    csrf: str,
    revision: int,
    step: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    response = client.put(
        f"/api/v1/businesses/{identity.business_id}/onboarding/steps/{step}",
        headers=csrf_headers(csrf),
        json={"step": step, "revision": revision, **data},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _complete_all_steps(
    client: TestClient,
    admin: Identity,
    reviewer: Identity,
    logo_id: UUID,
    reference_id: UUID,
) -> tuple[str, dict[str, Any]]:
    csrf = login(client, admin)
    state = _start(client, admin, csrf)
    inputs: list[tuple[int, dict[str, Any]]] = [
        (
            1,
            {
                "name": "Clínica Horizonte Animal",
                "brand_name": "Horizonte Animal",
                "public_name": "Clínica Horizonte",
                "description": "Atendimento veterinário preventivo e acolhedor.",
                "timezone": "America/Sao_Paulo",
            },
        ),
        (2, {"segment": "Clínica veterinária"}),
        (
            3,
            {
                "services": [
                    {
                        "name": "Consulta preventiva",
                        "description": "Acompanhamento periódico fictício.",
                        "category": "CONSULTA",
                        "warnings": ["Não substituir avaliação profissional"],
                    }
                ]
            },
        ),
        (
            4,
            {
                "audiences": [
                    {
                        "name": "Tutores responsáveis",
                        "description": "Pessoas interessadas em prevenção.",
                        "needs": ["Informação clara"],
                        "objections": ["Receio de linguagem técnica"],
                        "location": "São Paulo",
                    }
                ]
            },
        ),
        (
            5,
            {
                "objectives": [
                    {
                        "name": "Educação preventiva",
                        "description": "Orientar sem realizar diagnóstico.",
                        "planned_indicators": ["Conteúdos aprovados"],
                    }
                ]
            },
        ),
        (6, {"differentiators": ["Atendimento acolhedor", "Comunicação responsável"]}),
        (
            7,
            {
                "tone_of_voice": "Acolhedor, responsável e simples",
                "preferred_words": ["cuidado"],
                "forbidden_words": ["cura garantida"],
            },
        ),
        (8, {"logo_media_asset_ids": [str(logo_id)]}),
        (
            9,
            {
                "primary_colors": ["#14532D"],
                "secondary_colors": ["#DCFCE7"],
                "fonts": ["Inter"],
            },
        ),
        (10, {"visual_reference_media_asset_ids": [str(reference_id)]}),
        (
            11,
            {
                "allowed_rules": ["Usar linguagem educativa"],
                "forbidden_rules": ["Prometer diagnóstico ou cura"],
                "required_terms": ["Procure um médico-veterinário"],
                "legal_rules": ["Revisão humana antes da publicação"],
                "image_restrictions": ["Não exibir procedimento invasivo"],
            },
        ),
        (12, {"membership_ids": [str(reviewer.membership_id)]}),
        (
            13,
            {
                "email_enabled": True,
                "mode": "DAILY",
                "timezone": "America/Sao_Paulo",
                "digest_time": "09:30:00",
                "weekly_day": 1,
                "disabled_categories": ["REPORT_AVAILABLE"],
            },
        ),
        (
            14,
            {
                "preset": {
                    "name": "Feed educativo inicial",
                    "format": "FEED",
                    "aspect_ratio": "1:1",
                    "creation_mode": "HYBRID",
                    "color_palette": ["#14532D", "#DCFCE7"],
                    "fonts": ["Inter"],
                    "logo_media_asset_id": str(logo_id),
                    "allowed_elements": ["animais em ambiente acolhedor"],
                    "forbidden_elements": ["procedimentos invasivos"],
                }
            },
        ),
        (15, {"confirmed": True, "notes": "Dados fictícios revisados."}),
    ]
    for step, data in inputs:
        state = _save(client, admin, csrf, state["revision"], step, data)
    return csrf, state


def test_onboarding_persists_real_data_resumes_and_completes_idempotently(
    client: TestClient,
) -> None:
    admin = create_identity(
        slug="phase3-onboarding",
        email="onboarding-admin@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente em onboarding",
    )
    reviewer = add_user_to_identity(
        admin,
        email="onboarding-reviewer@example.test",
        role=Role.CLIENT_REVIEWER,
    )
    logo_id = create_ready_media(admin, display_name="logo.png")
    reference_id = create_ready_media(admin, display_name="referencia.png")

    csrf, state = _complete_all_steps(client, admin, reviewer, logo_id, reference_id)
    assert state["completed_steps"] == list(range(1, 16))
    assert state["missing_steps"] == []
    assert state["progress_percent"] == 100
    assert state["status"] == "IN_PROGRESS"
    assert state["step_data"]["3"]["services"][0]["name"] == "Consulta preventiva"
    assert state["step_data"]["13"]["mode"] == "DAILY"

    completion_revision = state["revision"]
    response = client.post(
        f"/api/v1/businesses/{admin.business_id}/onboarding/complete",
        headers=csrf_headers(csrf),
        json={"revision": completion_revision},
    )
    assert response.status_code == 200, response.text
    completed = response.json()
    assert completed["status"] == "COMPLETED"
    assert completed["missing_steps"] == []
    assert completed["revision"] == completion_revision + 1
    assert completed["summary"]["initial_preset_id"]

    repeated = client.post(
        f"/api/v1/businesses/{admin.business_id}/onboarding/complete",
        headers=csrf_headers(csrf),
        json={"revision": completion_revision},
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["revision"] == completed["revision"]

    resumed = client.get(f"/api/v1/businesses/{admin.business_id}/onboarding")
    assert resumed.status_code == 200
    assert resumed.json()["step_data"] == completed["step_data"]

    with get_session_factory()() as session:
        business = session.get(Business, admin.business_id)
        assert business is not None
        assert business.name == "Clínica Horizonte Animal"
        assert business.onboarding_status == "COMPLETED"
        assert business.onboarding_completed_at is not None
        brand = session.scalar(
            select(BrandProfile).where(BrandProfile.business_id == admin.business_id)
        )
        assert brand is not None
        assert brand.secondary_colors == ["#DCFCE7"]
        assert brand.fonts == ["Inter"]
        assert brand.logo_media_asset_ids == [str(logo_id)]
        assert brand.visual_reference_media_asset_ids == [str(reference_id)]
        assert brand.allowed_rules == ["Usar linguagem educativa"]
        assert session.scalar(
            select(Service).where(
                Service.business_id == admin.business_id,
                Service.name == "Consulta preventiva",
            )
        )
        assert session.scalar(
            select(VisualPreset).where(
                VisualPreset.business_id == admin.business_id,
                VisualPreset.name == "Feed educativo inicial",
            )
        )
        onboarding = session.scalar(
            select(BusinessOnboarding).where(BusinessOnboarding.business_id == admin.business_id)
        )
        assert onboarding is not None
        assert onboarding.status == "COMPLETED"
        actions = set(
            session.scalars(
                select(AuditLog.action).where(AuditLog.business_id == admin.business_id)
            ).all()
        )
        assert {"onboarding.started", "onboarding.step_saved", "onboarding.completed"} <= actions


def test_editing_completed_onboarding_requires_a_new_final_review(
    client: TestClient,
) -> None:
    admin = create_identity(
        slug="phase3-onboarding-reopen",
        email="onboarding-reopen-admin@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente concluído",
    )
    reviewer = add_user_to_identity(
        admin,
        email="onboarding-reopen-reviewer@example.test",
        role=Role.CLIENT_REVIEWER,
    )
    logo_id = create_ready_media(admin, display_name="logo-reopen.png")
    reference_id = create_ready_media(admin, display_name="reference-reopen.png")
    csrf, ready = _complete_all_steps(client, admin, reviewer, logo_id, reference_id)
    response = client.post(
        f"/api/v1/businesses/{admin.business_id}/onboarding/complete",
        headers=csrf_headers(csrf),
        json={"revision": ready["revision"]},
    )
    assert response.status_code == 200, response.text
    completed = response.json()

    reopened = _save(
        client,
        admin,
        csrf,
        completed["revision"],
        2,
        {"segment": "Hospital veterinário fictício"},
    )

    assert reopened["status"] == "IN_PROGRESS"
    assert reopened["completed_at"] is None
    assert reopened["completed_by_user_id"] is None
    assert 15 not in reopened["completed_steps"]
    assert reopened["missing_steps"] == [15]
    assert "15" not in reopened["step_data"]

    premature = client.post(
        f"/api/v1/businesses/{admin.business_id}/onboarding/complete",
        headers=csrf_headers(csrf),
        json={"revision": reopened["revision"]},
    )
    assert premature.status_code == 409

    reviewed = _save(
        client,
        admin,
        csrf,
        reopened["revision"],
        15,
        {"confirmed": True, "notes": "Alteração revisada novamente."},
    )
    concluded_again = client.post(
        f"/api/v1/businesses/{admin.business_id}/onboarding/complete",
        headers=csrf_headers(csrf),
        json={"revision": reviewed["revision"]},
    )
    assert concluded_again.status_code == 200, concluded_again.text
    assert concluded_again.json()["status"] == "COMPLETED"

    with get_session_factory()() as session:
        business = session.get(Business, admin.business_id)
        assert business is not None
        assert business.onboarding_status == "COMPLETED"
        assert business.onboarding_completed_at is not None
        reopened_events = session.scalars(
            select(AuditLog).where(
                AuditLog.business_id == admin.business_id,
                AuditLog.action == "onboarding.reopened",
            )
        ).all()
        assert len(reopened_events) == 1
        assert reopened_events[0].details["step"] == 2


def test_onboarding_archives_only_managed_catalog_items_omitted_by_an_edit(
    client: TestClient,
) -> None:
    admin = create_identity(
        slug="phase3-onboarding-catalog-removal",
        email="onboarding-catalog-removal@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente com catálogo",
    )
    csrf = login(client, admin)
    state = _start(client, admin, csrf)
    state = _save(
        client,
        admin,
        csrf,
        state["revision"],
        3,
        {
            "services": [
                {"name": "Consulta", "description": "A", "category": "A"},
                {"name": "Vacinação", "description": "B", "category": "B"},
            ]
        },
    )
    first, removed = state["step_data"]["3"]["services"]
    with get_session_factory()() as session:
        unmanaged = Service(
            organization_id=admin.organization_id,
            business_id=admin.business_id,
            name="Serviço criado fora do onboarding",
        )
        session.add(unmanaged)
        session.commit()
        unmanaged_id = unmanaged.id

    edited = _save(
        client,
        admin,
        csrf,
        state["revision"],
        3,
        {
            "services": [
                {
                    "id": first["id"],
                    "name": first["name"],
                    "description": "Atualizada",
                    "category": first["category"],
                }
            ]
        },
    )

    assert [item["id"] for item in edited["step_data"]["3"]["services"]] == [first["id"]]
    assert removed["id"] not in edited["summary"]["service_ids"]
    assert str(unmanaged_id) in edited["summary"]["service_ids"]
    with get_session_factory()() as session:
        removed_service = session.get(Service, UUID(removed["id"]))
        unmanaged_service = session.get(Service, unmanaged_id)
        assert removed_service is not None
        assert removed_service.is_active is False
        assert removed_service.archived_at is not None
        assert unmanaged_service is not None
        assert unmanaged_service.is_active is True
        assert unmanaged_service.archived_at is None


def test_onboarding_validates_payload_and_optimistic_revision(client: TestClient) -> None:
    admin = create_identity(
        slug="phase3-onboarding-validation",
        email="onboarding-validation@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente validação",
    )
    csrf = login(client, admin)
    state = _start(client, admin, csrf)

    invalid = client.put(
        f"/api/v1/businesses/{admin.business_id}/onboarding/steps/1",
        headers=csrf_headers(csrf),
        json={
            "step": 1,
            "revision": state["revision"],
            "name": "Cliente",
            "brand_name": "Cliente",
            "timezone": "Fuso/Inexistente",
            "campo_inesperado": "não permitido",
        },
    )
    assert invalid.status_code == 422

    saved = _save(
        client,
        admin,
        csrf,
        state["revision"],
        1,
        {
            "name": "Cliente salvo",
            "brand_name": "Cliente salvo",
            "timezone": "America/Sao_Paulo",
        },
    )
    assert saved["revision"] == state["revision"] + 1
    assert saved["current_step"] == 2
    assert saved["step_data"]["1"]["name"] == "Cliente salvo"

    stale = client.put(
        f"/api/v1/businesses/{admin.business_id}/onboarding/steps/1",
        headers=csrf_headers(csrf),
        json={
            "step": 1,
            "revision": state["revision"],
            "name": "Sobrescrita indevida",
            "brand_name": "Sobrescrita",
            "timezone": "America/Sao_Paulo",
        },
    )
    assert stale.status_code == 409

    mismatch = client.put(
        f"/api/v1/businesses/{admin.business_id}/onboarding/steps/2",
        headers=csrf_headers(csrf),
        json={"step": 1, "revision": saved["revision"], "name": "Xx", "brand_name": "X"},
    )
    assert mismatch.status_code == 422

    incomplete = client.post(
        f"/api/v1/businesses/{admin.business_id}/onboarding/complete",
        headers=csrf_headers(csrf),
        json={"revision": saved["revision"]},
    )
    assert incomplete.status_code == 409
    assert "etapas" in incomplete.json()["detail"]

    with get_session_factory()() as session:
        business = session.get(Business, admin.business_id)
        assert business is not None
        assert business.name == "Cliente salvo"


def test_onboarding_rejects_cross_tenant_resources_and_businesses(client: TestClient) -> None:
    first = create_identity(
        slug="phase3-onboarding-first",
        email="onboarding-first@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente A",
    )
    second = create_identity(
        slug="phase3-onboarding-second",
        email="onboarding-second@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente B",
    )
    foreign_media = create_ready_media(second)
    csrf = login(client, first)
    state = _start(client, first, csrf)

    business_attack = client.post(
        f"/api/v1/businesses/{second.business_id}/onboarding",
        headers=csrf_headers(csrf),
    )
    assert business_attack.status_code == 404

    media_attack = client.put(
        f"/api/v1/businesses/{first.business_id}/onboarding/steps/8",
        headers=csrf_headers(csrf),
        json={
            "step": 8,
            "revision": state["revision"],
            "logo_media_asset_ids": [str(foreign_media)],
        },
    )
    assert media_attack.status_code == 404

    reviewer_attack = client.put(
        f"/api/v1/businesses/{first.business_id}/onboarding/steps/12",
        headers=csrf_headers(csrf),
        json={
            "step": 12,
            "revision": state["revision"],
            "membership_ids": [str(second.membership_id)],
        },
    )
    assert reviewer_attack.status_code == 404

    resumed = client.get(f"/api/v1/businesses/{first.business_id}/onboarding")
    assert resumed.status_code == 200
    assert 8 not in resumed.json()["completed_steps"]
    assert 12 not in resumed.json()["completed_steps"]


def test_only_admin_and_strategist_manage_onboarding(client: TestClient) -> None:
    admin = create_identity(
        slug="phase3-onboarding-rbac",
        email="onboarding-rbac-admin@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente RBAC",
    )
    editor = add_user_to_identity(
        admin,
        email="onboarding-rbac-editor@example.test",
        role=Role.CONTENT_EDITOR,
    )
    strategist = add_user_to_identity(
        admin,
        email="onboarding-rbac-strategist@example.test",
        role=Role.STRATEGIST,
    )
    admin_csrf = login(client, admin)
    _start(client, admin, admin_csrf)

    editor_csrf = login(client, editor)
    denied_get = client.get(f"/api/v1/businesses/{admin.business_id}/onboarding")
    assert denied_get.status_code == 403
    denied_write = client.post(
        f"/api/v1/businesses/{admin.business_id}/onboarding",
        headers=csrf_headers(editor_csrf),
    )
    assert denied_write.status_code == 403

    strategist_csrf = login(client, strategist)
    allowed = client.post(
        f"/api/v1/businesses/{admin.business_id}/onboarding",
        headers=csrf_headers(strategist_csrf),
    )
    assert allowed.status_code == 200
    assert allowed.json()["business_id"] == str(admin.business_id)

    with get_session_factory()() as session:
        memberships = session.scalars(
            select(Membership).where(Membership.organization_id == admin.organization_id)
        ).all()
        assert len(memberships) == 3
