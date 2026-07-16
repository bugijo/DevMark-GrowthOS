from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import (
    AudienceSegment,
    AuditLog,
    BrandProfile,
    Business,
    CalendarEntry,
    ContentPlan,
    ContentStrategy,
    ContentVersion,
    ContentVersionMedia,
    Job,
    MarketingObjective,
    MediaAsset,
    Service,
    StrategyVersion,
    VisualPreset,
)
from tests.conftest import Identity, add_user_to_identity, create_identity, csrf_headers, login


@dataclass(frozen=True)
class LinkedContentFixture:
    identity: Identity
    reviewer: Identity
    brand_id: UUID
    service_id: UUID
    audience_id: UUID
    objective_id: UUID
    strategy_id: UUID
    strategy_version_id: UUID
    plan_id: UUID
    calendar_entry_id: UUID
    preset_id: UUID
    media_id: UUID
    pending_media_id: UUID


@dataclass(frozen=True)
class VisualResources:
    business_id: UUID
    preset_id: UUID
    media_id: UUID


def _media_asset(
    identity: Identity,
    *,
    business_id: UUID,
    suffix: str,
    processing_status: str = "READY",
) -> MediaAsset:
    return MediaAsset(
        organization_id=identity.organization_id,
        business_id=business_id,
        kind="IMAGE",
        storage_provider="memory",
        object_key=f"{identity.organization_id}/{business_id}/{suffix}.png",
        display_name=f"Imagem {suffix}",
        mime_type="image/png",
        byte_size=128,
        checksum_sha256=(suffix[0] if suffix else "a") * 64,
        width=1080,
        height=1080,
        origin="UPLOAD",
        processing_status=processing_status,
        metadata_safe={"fixture": True},
        created_by_user_id=identity.user_id,
    )


def _visual_preset(
    identity: Identity,
    *,
    business_id: UUID,
    brand_id: UUID,
    suffix: str,
) -> VisualPreset:
    return VisualPreset(
        organization_id=identity.organization_id,
        business_id=business_id,
        brand_profile_id=brand_id,
        name=f"Preset {suffix}",
        objective="Educar com clareza e responsabilidade",
        format="FEED",
        aspect_ratio="1:1",
        creation_mode="HYBRID",
        color_palette=["#14532D", "#F7F4EA"],
        fonts=["Inter"],
        logo_position="inferior direito",
        logo_scale_percent=16,
        safe_margins={"top": 8, "right": 8, "bottom": 10, "left": 8},
        background_style="consultório claro e organizado",
        photographic_style="fotografia documental acolhedora",
        realism_level="alto",
        lighting="luz natural suave",
        composition="animal e tutor em plano médio",
        max_text_characters=80,
        text_rules=["uma mensagem por peça"],
        base_prompt="cena veterinária preventiva e acolhedora",
        negative_prompt="ferimentos, procedimentos invasivos",
        allowed_elements=["animais tranquilos", "equipe acolhedora"],
        forbidden_elements=["ferimentos", "promessas terapêuticas"],
        visual_signature="formas orgânicas verdes",
        default_cta="Converse com a equipe.",
        created_by_user_id=identity.user_id,
        updated_by_user_id=identity.user_id,
    )


def _create_linked_fixture(slug: str) -> LinkedContentFixture:
    identity = create_identity(
        slug=slug,
        email=f"{slug}-admin@example.com",
        role=Role.AGENCY_ADMIN,
        business_name=f"Clínica {slug}",
    )
    reviewer = add_user_to_identity(
        identity,
        email=f"{slug}-reviewer@example.com",
        role=Role.CLIENT_REVIEWER,
        password="reviewer-password-123",
    )
    assert identity.business_id is not None

    with get_session_factory()() as session:
        brand = BrandProfile(
            organization_id=identity.organization_id,
            business_id=identity.business_id,
            brand_name=f"Clínica {slug}",
            public_name=f"Clínica {slug}",
            segment="Veterinária",
            audience="Tutores que valorizam prevenção responsável",
            primary_colors=["#14532D", "#F7F4EA"],
            tone_of_voice="acolhedor e responsável",
            preferred_words=["prevenção", "cuidado"],
            forbidden_words=["cura garantida"],
            calls_to_action=["Converse com a equipe."],
        )
        session.add(brand)
        session.flush()

        service = Service(
            organization_id=identity.organization_id,
            business_id=identity.business_id,
            name="Consulta preventiva",
            description="Atendimento fictício de prevenção.",
        )
        audience = AudienceSegment(
            organization_id=identity.organization_id,
            business_id=identity.business_id,
            name="Tutores de primeira viagem",
            description="Pessoas buscando informação preventiva clara.",
        )
        objective = MarketingObjective(
            organization_id=identity.organization_id,
            business_id=identity.business_id,
            name="Educação preventiva",
            description="Aumentar a clareza do conteúdo.",
        )
        media = _media_asset(identity, business_id=identity.business_id, suffix=f"{slug}-ready")
        pending_media = _media_asset(
            identity,
            business_id=identity.business_id,
            suffix=f"{slug}-pending",
            processing_status="PENDING",
        )
        session.add_all([service, audience, objective, media, pending_media])
        session.flush()

        preset = _visual_preset(
            identity,
            business_id=identity.business_id,
            brand_id=brand.id,
            suffix=slug,
        )
        session.add(preset)
        session.flush()

        strategy = ContentStrategy(
            organization_id=identity.organization_id,
            business_id=identity.business_id,
            name=f"Estratégia {slug}",
            starts_on=date(2026, 8, 1),
            ends_on=date(2026, 8, 31),
            status="APPROVED",
            created_by_user_id=identity.user_id,
        )
        session.add(strategy)
        session.flush()
        strategy_version = StrategyVersion(
            organization_id=identity.organization_id,
            business_id=identity.business_id,
            content_strategy_id=strategy.id,
            version_number=1,
            objective="Educar sobre prevenção responsável",
            positioning="Referência local em cuidado responsável",
            funnel=["AWARENESS"],
            channels=["INSTAGRAM"],
            pillars=["prevenção"],
            service_snapshots=[{"id": str(service.id), "name": service.name}],
            audience_snapshots=[{"id": str(audience.id), "name": audience.name}],
            objective_snapshots=[{"id": str(objective.id), "name": objective.name}],
            brand_context_snapshot={"brand_name": brand.brand_name},
            source="MANUAL",
            provider_name="mock",
            created_by_user_id=identity.user_id,
        )
        session.add(strategy_version)
        session.flush()
        strategy.current_version_id = strategy_version.id
        strategy.approved_version_id = strategy_version.id

        plan = ContentPlan(
            organization_id=identity.organization_id,
            business_id=identity.business_id,
            content_strategy_id=strategy.id,
            strategy_version_id=strategy_version.id,
            name=f"Plano {slug}",
            starts_on=date(2026, 8, 1),
            ends_on=date(2026, 8, 31),
            frequency="SEMANAL",
            status="ACTIVE",
            created_by_user_id=identity.user_id,
        )
        session.add(plan)
        session.flush()
        calendar_entry = CalendarEntry(
            organization_id=identity.organization_id,
            business_id=identity.business_id,
            content_plan_id=plan.id,
            visual_preset_id=preset.id,
            title="Vacinação preventiva",
            objective="Explicar prevenção com clareza",
            audience="Tutores de primeira viagem",
            channel="INSTAGRAM",
            format="FEED",
            suggested_for=datetime(2026, 8, 5, 12, tzinfo=UTC),
            status="PLANNED",
            created_by_user_id=identity.user_id,
        )
        session.add(calendar_entry)
        session.commit()
        return LinkedContentFixture(
            identity=identity,
            reviewer=reviewer,
            brand_id=brand.id,
            service_id=service.id,
            audience_id=audience.id,
            objective_id=objective.id,
            strategy_id=strategy.id,
            strategy_version_id=strategy_version.id,
            plan_id=plan.id,
            calendar_entry_id=calendar_entry.id,
            preset_id=preset.id,
            media_id=media.id,
            pending_media_id=pending_media.id,
        )


def _generation_payload(
    fixture: LinkedContentFixture,
    *,
    include_calendar: bool = True,
) -> dict[str, str]:
    payload = {
        "business_id": str(fixture.identity.business_id),
        "objective": "Explicar a importância da vacinação preventiva",
        "channel": "INSTAGRAM",
        "format": "FEED",
        "content_strategy_id": str(fixture.strategy_id),
        "strategy_version_id": str(fixture.strategy_version_id),
        "content_plan_id": str(fixture.plan_id),
        "visual_preset_id": str(fixture.preset_id),
        "service_id": str(fixture.service_id),
        "audience_segment_id": str(fixture.audience_id),
        "marketing_objective_id": str(fixture.objective_id),
        "media_asset_id": str(fixture.media_id),
        "notes": "Validar a informação com profissional responsável.",
        "script": "Apresente a prevenção sem prometer resultado clínico.",
    }
    if include_calendar:
        payload["calendar_entry_id"] = str(fixture.calendar_entry_id)
    return payload


def _generate(
    client: TestClient,
    headers: dict[str, str],
    fixture: LinkedContentFixture,
    *,
    include_calendar: bool = True,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/contents/generate",
        json=_generation_payload(fixture, include_calendar=include_calendar),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _send_to_client(
    client: TestClient,
    headers: dict[str, str],
    content_id: object,
) -> dict[str, object]:
    submitted = client.post(
        f"/api/v1/contents/{content_id}/submit-internal",
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    sent = client.post(
        f"/api/v1/contents/{content_id}/send-to-client",
        headers=headers,
    )
    assert sent.status_code == 200, sent.text
    return sent.json()


def _add_visual_resources(
    identity: Identity,
    *,
    suffix: str,
    create_business: bool = False,
) -> VisualResources:
    assert identity.business_id is not None
    with get_session_factory()() as session:
        if create_business:
            business = Business(
                organization_id=identity.organization_id,
                name=f"Outra clínica {suffix}",
                segment="Veterinária",
            )
            session.add(business)
            session.flush()
            business_id = business.id
            brand = BrandProfile(
                organization_id=identity.organization_id,
                business_id=business_id,
                brand_name=f"Outra clínica {suffix}",
                audience="Outro público",
                tone_of_voice="informativo",
            )
            session.add(brand)
            session.flush()
        else:
            business_id = identity.business_id
            brand = session.scalar(
                select(BrandProfile).where(
                    BrandProfile.organization_id == identity.organization_id,
                    BrandProfile.business_id == business_id,
                )
            )
            assert brand is not None
        media = _media_asset(identity, business_id=business_id, suffix=suffix)
        preset = _visual_preset(
            identity,
            business_id=business_id,
            brand_id=brand.id,
            suffix=suffix,
        )
        session.add_all([media, preset])
        session.commit()
        return VisualResources(business_id=business_id, preset_id=preset.id, media_id=media.id)


def _approval_statuses(content: dict[str, object]) -> dict[str, str]:
    approvals = content["approvals"]
    assert isinstance(approvals, list)
    return {approval["component"]: approval["status"] for approval in approvals}


def test_generation_persists_scoped_links_mock_prompt_media_and_snapshots(
    client: TestClient,
) -> None:
    fixture = _create_linked_fixture("content-links")
    headers = csrf_headers(login(client, fixture.identity))
    generated = _generate(client, headers, fixture)

    assert generated["status"] == "DRAFT"
    assert generated["content_strategy_id"] == str(fixture.strategy_id)
    assert generated["strategy_version_id"] == str(fixture.strategy_version_id)
    assert generated["content_plan_id"] == str(fixture.plan_id)
    assert generated["calendar_entry_id"] == str(fixture.calendar_entry_id)
    assert generated["visual_preset_id"] == str(fixture.preset_id)
    version = generated["current_version"]
    assert version["service_id"] == str(fixture.service_id)
    assert version["audience_segment_id"] == str(fixture.audience_id)
    assert version["marketing_objective_id"] == str(fixture.objective_id)
    assert version["media_asset_ids"] == [str(fixture.media_id)]
    assert version["notes"] == "Validar a informação com profissional responsável."
    assert version["script"] == "Apresente a prevenção sem prometer resultado clínico."
    assert "Clínica content-links" in version["visual_prompt"]
    assert "ferimentos" in version["negative_prompt"]
    assert version["brand_context_snapshot"]["brand_name"] == "Clínica content-links"
    assert version["visual_preset_snapshot"]["id"] == str(fixture.preset_id)
    assert version["visual_preset_snapshot"]["prompt_provider"] == "mock"

    with get_session_factory()() as session:
        calendar_entry = session.get(CalendarEntry, fixture.calendar_entry_id)
        brand = session.get(BrandProfile, fixture.brand_id)
        preset = session.get(VisualPreset, fixture.preset_id)
        association = session.scalar(
            select(ContentVersionMedia).where(
                ContentVersionMedia.content_version_id == UUID(version["id"])
            )
        )
        assert calendar_entry is not None
        assert calendar_entry.content_item_id == UUID(generated["id"])
        assert calendar_entry.status == "GENERATED"
        assert association is not None
        assert association.organization_id == fixture.identity.organization_id
        assert association.business_id == fixture.identity.business_id
        assert association.media_asset_id == fixture.media_id
        assert association.role == "PRIMARY"
        assert brand is not None
        assert preset is not None
        brand.brand_name = "Marca alterada depois da geração"
        preset.base_prompt = "Prompt alterado depois da geração"
        preset.version += 1
        session.commit()

    persisted = client.get(f"/api/v1/contents/{generated['id']}")
    assert persisted.status_code == 200, persisted.text
    persisted_version = persisted.json()["current_version"]
    assert persisted_version["brand_context_snapshot"]["brand_name"] == ("Clínica content-links")
    assert persisted_version["visual_preset_snapshot"]["base_prompt"] == (
        "cena veterinária preventiva e acolhedora"
    )
    assert persisted_version["visual_preset_snapshot"]["version"] == 1


def test_generation_rejects_every_cross_tenant_link_and_non_ready_media(
    client: TestClient,
) -> None:
    own = _create_linked_fixture("content-own")
    other = _create_linked_fixture("content-other")
    headers = csrf_headers(login(client, own.identity))
    cross_tenant_values = {
        "content_strategy_id": other.strategy_id,
        "strategy_version_id": other.strategy_version_id,
        "content_plan_id": other.plan_id,
        "calendar_entry_id": other.calendar_entry_id,
        "visual_preset_id": other.preset_id,
        "service_id": other.service_id,
        "audience_segment_id": other.audience_id,
        "marketing_objective_id": other.objective_id,
        "media_asset_id": other.media_id,
    }
    for field, resource_id in cross_tenant_values.items():
        response = client.post(
            "/api/v1/contents/generate",
            json={
                "business_id": str(own.identity.business_id),
                "objective": "Tentativa de associação cruzada",
                field: str(resource_id),
            },
            headers=headers,
        )
        assert response.status_code == 404, (field, response.text)
        assert str(resource_id) not in response.text

    pending_media = client.post(
        "/api/v1/contents/generate",
        json={
            "business_id": str(own.identity.business_id),
            "objective": "Tentar usar mídia ainda não validada",
            "media_asset_id": str(own.pending_media_id),
        },
        headers=headers,
    )
    assert pending_media.status_code == 404
    assert str(own.pending_media_id) not in pending_media.text


def test_client_decides_text_and_image_separately_and_can_request_image_changes(
    client: TestClient,
) -> None:
    fixture = _create_linked_fixture("content-decisions")
    headers = csrf_headers(login(client, fixture.identity))
    generated = _generate(client, headers, fixture)
    sent = _send_to_client(client, headers, generated["id"])
    assert sent["status"] == "CLIENT_REVIEW"
    assert _approval_statuses(sent) == {"IMAGE": "PENDING", "TEXT": "PENDING"}
    with get_session_factory()() as session:
        review_jobs = list(
            session.scalars(
                select(Job).where(
                    Job.organization_id == fixture.identity.organization_id,
                    Job.idempotency_key.like(f"content-review:{generated['id']}:%"),
                )
            ).all()
        )
    assert len(review_jobs) == 1
    assert review_jobs[0].type == "notification.email.smtp"
    assert set(review_jobs[0].payload) == {"to", "subject", "text"}
    assert generated["current_version"]["caption"] not in review_jobs[0].payload.values()
    assert generated["current_version"]["visual_prompt"] not in review_jobs[0].payload.values()

    reviewer_client = TestClient(client.app)
    reviewer_headers = csrf_headers(login(reviewer_client, fixture.reviewer))
    text_decision = reviewer_client.post(
        f"/api/v1/contents/{generated['id']}/decisions/TEXT/approve",
        json={"comment": "Texto aprovado"},
        headers=reviewer_headers,
    )
    assert text_decision.status_code == 200, text_decision.text
    assert text_decision.json()["status"] == "CLIENT_REVIEW"
    assert _approval_statuses(text_decision.json()) == {
        "IMAGE": "PENDING",
        "TEXT": "APPROVED",
    }
    with get_session_factory()() as session:
        decision_jobs = list(
            session.scalars(
                select(Job).where(
                    Job.organization_id == fixture.identity.organization_id,
                    Job.idempotency_key.like(f"content-decision:{generated['id']}:%"),
                )
            ).all()
        )
    assert len(decision_jobs) == 1
    assert set(decision_jobs[0].payload) == {"to", "subject", "text"}
    assert "Texto aprovado" not in decision_jobs[0].payload.values()

    image_decision = reviewer_client.post(
        f"/api/v1/contents/{generated['id']}/decisions/IMAGE/approve",
        json={"comment": "Imagem aprovada"},
        headers=reviewer_headers,
    )
    assert image_decision.status_code == 200, image_decision.text
    assert image_decision.json()["status"] == "APPROVED"
    assert _approval_statuses(image_decision.json()) == {
        "IMAGE": "APPROVED",
        "TEXT": "APPROVED",
    }

    another = _generate(client, headers, fixture, include_calendar=False)
    requested = _send_to_client(client, headers, another["id"])
    assert _approval_statuses(requested) == {"IMAGE": "PENDING", "TEXT": "PENDING"}
    image_changes = reviewer_client.post(
        f"/api/v1/contents/{another['id']}/decisions/IMAGE/request-changes",
        json={"comment": "Trocar a imagem por uma cena mais clara"},
        headers=reviewer_headers,
    )
    assert image_changes.status_code == 200, image_changes.text
    assert image_changes.json()["status"] == "CHANGES_REQUESTED"
    assert image_changes.json()["change_request_comment"] == (
        "Trocar a imagem por uma cena mais clara"
    )
    assert _approval_statuses(image_changes.json()) == {
        "IMAGE": "CHANGES_REQUESTED",
        "TEXT": "CANCELLED",
    }


def test_designer_creates_immutable_scoped_visual_revision_but_cannot_edit_text(
    client: TestClient,
) -> None:
    fixture = _create_linked_fixture("content-visual")
    designer = add_user_to_identity(
        fixture.identity,
        email="content-visual-designer@example.com",
        role=Role.DESIGNER,
        password="designer-password-123",
    )
    headers = csrf_headers(login(client, fixture.identity))
    generated = _generate(client, headers, fixture)
    _send_to_client(client, headers, generated["id"])

    reviewer_client = TestClient(client.app)
    reviewer_headers = csrf_headers(login(reviewer_client, fixture.reviewer))
    changes = reviewer_client.post(
        f"/api/v1/contents/{generated['id']}/decisions/IMAGE/request-changes",
        json={"comment": "Usar outra composição visual"},
        headers=reviewer_headers,
    )
    assert changes.status_code == 200, changes.text

    designer_client = TestClient(client.app)
    designer_headers = csrf_headers(login(designer_client, designer))
    original_version = generated["current_version"]
    forbidden_text_revision = designer_client.post(
        f"/api/v1/contents/{generated['id']}/revisions",
        json={
            "title": original_version["title"],
            "caption": f"{original_version['caption']} Texto alterado.",
            "cta": original_version["cta"],
        },
        headers=designer_headers,
    )
    assert forbidden_text_revision.status_code == 403

    other_business = _add_visual_resources(
        fixture.identity,
        suffix="cross-business",
        create_business=True,
    )
    cross_preset = designer_client.post(
        f"/api/v1/contents/{generated['id']}/visual-revisions",
        json={"visual_preset_id": str(other_business.preset_id)},
        headers=designer_headers,
    )
    assert cross_preset.status_code == 404
    assert str(other_business.preset_id) not in cross_preset.text
    cross_media = designer_client.post(
        f"/api/v1/contents/{generated['id']}/visual-revisions",
        json={"media_asset_id": str(other_business.media_id)},
        headers=designer_headers,
    )
    assert cross_media.status_code == 404
    assert str(other_business.media_id) not in cross_media.text
    pending_media = designer_client.post(
        f"/api/v1/contents/{generated['id']}/visual-revisions",
        json={"media_asset_id": str(fixture.pending_media_id)},
        headers=designer_headers,
    )
    assert pending_media.status_code == 404

    replacement = _add_visual_resources(fixture.identity, suffix="replacement")
    revised = designer_client.post(
        f"/api/v1/contents/{generated['id']}/visual-revisions",
        json={
            "visual_preset_id": str(replacement.preset_id),
            "media_asset_id": str(replacement.media_id),
            "visual_prompt": "Cena clara com tutor e animal em consulta preventiva.",
            "negative_prompt": "ferimentos, procedimentos invasivos, texto ilegível",
        },
        headers=designer_headers,
    )
    assert revised.status_code == 200, revised.text
    revised_content = revised.json()
    revised_version = revised_content["current_version"]
    assert revised_content["status"] == "DRAFT"
    assert revised_content["visual_preset_id"] == str(replacement.preset_id)
    assert revised_version["id"] != original_version["id"]
    assert revised_version["version_number"] == 2
    assert revised_version["title"] == original_version["title"]
    assert revised_version["caption"] == original_version["caption"]
    assert revised_version["visual_prompt"] == (
        "Cena clara com tutor e animal em consulta preventiva."
    )
    assert revised_version["negative_prompt"] == (
        "ferimentos, procedimentos invasivos, texto ilegível"
    )
    assert str(replacement.media_id) in revised_version["media_asset_ids"]
    assert revised_version["visual_preset_snapshot"]["id"] == str(replacement.preset_id)

    with get_session_factory()() as session:
        old_version = session.get(ContentVersion, UUID(original_version["id"]))
        new_version = session.get(ContentVersion, UUID(revised_version["id"]))
        old_media = set(
            session.scalars(
                select(ContentVersionMedia.media_asset_id).where(
                    ContentVersionMedia.content_version_id == UUID(original_version["id"])
                )
            ).all()
        )
        new_media = set(
            session.scalars(
                select(ContentVersionMedia.media_asset_id).where(
                    ContentVersionMedia.content_version_id == UUID(revised_version["id"])
                )
            ).all()
        )
        assert old_version is not None
        assert new_version is not None
        assert old_version.visual_prompt == original_version["visual_prompt"]
        assert old_version.negative_prompt == original_version["negative_prompt"]
        assert old_version.visual_preset_snapshot["id"] == str(fixture.preset_id)
        assert old_media == {fixture.media_id}
        assert replacement.media_id in new_media
        assert new_version.created_by_user_id == designer.user_id


def test_manual_publication_is_idempotent_audited_and_creates_no_external_job(
    client: TestClient,
) -> None:
    fixture = _create_linked_fixture("content-publication")
    headers = csrf_headers(login(client, fixture.identity))
    generated = _generate(client, headers, fixture)
    _send_to_client(client, headers, generated["id"])

    reviewer_client = TestClient(client.app)
    reviewer_headers = csrf_headers(login(reviewer_client, fixture.reviewer))
    approved = reviewer_client.post(
        f"/api/v1/contents/{generated['id']}/approve",
        json={"comment": "Texto e imagem aprovados"},
        headers=reviewer_headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"

    with get_session_factory()() as session:
        jobs_before = session.scalar(select(func.count(Job.id)))

    publication_payload = {
        "channel": "INSTAGRAM",
        "published_at": "2026-08-05T15:30:00Z",
        "reference": "https://example.com/publicacao-manual-001",
        "idempotency_key": "manual-publication-content-001",
    }
    published = client.post(
        f"/api/v1/contents/{generated['id']}/publication",
        json=publication_payload,
        headers=headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "PUBLISHED"
    assert published.json()["publication_channel"] == "INSTAGRAM"
    assert published.json()["publication_reference"] == publication_payload["reference"]
    assert published.json()["published_by_user_id"] == str(fixture.identity.user_id)

    replay = client.post(
        f"/api/v1/contents/{generated['id']}/publication",
        json={
            **publication_payload,
            "published_at": "2026-08-06T15:30:00Z",
            "reference": "https://example.com/nao-deve-substituir",
        },
        headers=headers,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["published_at"].removesuffix("Z") == published.json()[
        "published_at"
    ].removesuffix("Z")
    assert replay.json()["publication_reference"] == publication_payload["reference"]

    with get_session_factory()() as session:
        jobs_after = session.scalar(select(func.count(Job.id)))
        publication_audits = list(
            session.scalars(
                select(AuditLog).where(
                    AuditLog.organization_id == fixture.identity.organization_id,
                    AuditLog.resource_id == UUID(generated["id"]),
                    AuditLog.action == "content.publication_recorded",
                )
            ).all()
        )
        calendar_entry = session.get(CalendarEntry, fixture.calendar_entry_id)
    assert jobs_after == jobs_before
    assert len(publication_audits) == 1
    assert publication_audits[0].details["automatic_publication"] is False
    assert calendar_entry is not None
    assert calendar_entry.status == "PUBLISHED"
