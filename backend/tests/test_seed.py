import io
import re
from datetime import UTC, datetime
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from growthos.config import get_settings
from growthos.database import get_session_factory
from growthos.domain.enums import (
    ApprovalComponent,
    ApprovalStatus,
    ContentStatus,
    NotificationCategory,
    NotificationImportance,
    Role,
)
from growthos.models import (
    Approval,
    AudienceSegment,
    BrandProfile,
    Business,
    BusinessOnboarding,
    CalendarEntry,
    ContentItem,
    ContentPlan,
    ContentStrategy,
    ContentVersion,
    ContentVersionMedia,
    MarketingObjective,
    MediaAsset,
    Membership,
    Notification,
    NotificationCategoryPreference,
    NotificationPreference,
    Organization,
    Service,
    StrategyVersion,
    User,
    VisualPreset,
)
from growthos.security import hash_password
from growthos.seed import seed_demo
from growthos.services.storage import MemoryStorageProvider
from tests.conftest import csrf_headers


def _append_content_revision(
    session: Session,
    content: ContentItem,
    current: ContentVersion,
) -> ContentVersion:
    revision = ContentVersion(
        organization_id=current.organization_id,
        business_id=current.business_id,
        content_item_id=current.content_item_id,
        version_number=current.version_number + 1,
        title=current.title,
        caption=f"{current.caption} Revisão posterior preservada pelo teste.",
        channel=current.channel,
        format=current.format,
        objective=current.objective,
        audience=current.audience,
        cta=current.cta,
        service_id=current.service_id,
        audience_segment_id=current.audience_segment_id,
        marketing_objective_id=current.marketing_objective_id,
        notes=current.notes,
        script=current.script,
        visual_prompt=current.visual_prompt,
        negative_prompt=current.negative_prompt,
        brand_context_snapshot=dict(current.brand_context_snapshot),
        visual_preset_snapshot=dict(current.visual_preset_snapshot),
        provider_name="manual_revision",
        created_by_user_id=current.created_by_user_id,
    )
    session.add(revision)
    session.flush()
    content.current_version_id = revision.id
    return revision


def test_seed_is_idempotent_and_uses_distinct_client_credentials() -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        first = seed_demo(session, storage=storage)
        second = seed_demo(session, storage=storage)
        assert first == second
        assert session.scalar(select(func.count()).select_from(Organization)) == 1
        assert session.scalar(select(func.count()).select_from(User)) == 2
        assert session.scalar(select(func.count()).select_from(Membership)) == 2
        assert session.scalar(select(func.count()).select_from(Service)) == 3
        assert session.scalar(select(func.count()).select_from(AudienceSegment)) == 3
        assert session.scalar(select(func.count()).select_from(MarketingObjective)) == 3
        assert session.scalar(select(func.count()).select_from(VisualPreset)) == 2
        assert session.scalar(select(func.count()).select_from(ContentStrategy)) == 1
        assert session.scalar(select(func.count()).select_from(StrategyVersion)) == 2
        assert session.scalar(select(func.count()).select_from(ContentPlan)) == 1
        assert session.scalar(select(func.count()).select_from(CalendarEntry)) == 5
        assert session.scalar(select(func.count()).select_from(ContentItem)) == 5
        assert session.scalar(select(func.count()).select_from(ContentVersion)) == 6
        assert session.scalar(select(func.count()).select_from(MediaAsset)) == 4
        assert session.scalar(select(func.count()).select_from(ContentVersionMedia)) == 5
        assert session.scalar(select(func.count()).select_from(Approval)) == 10
        assert session.scalar(select(func.count()).select_from(Notification)) == 3
        assert session.scalar(select(func.count()).select_from(NotificationPreference)) == 1
        assert session.scalar(
            select(func.count()).select_from(NotificationCategoryPreference)
        ) == len(NotificationCategory)
        assert session.scalar(select(func.count()).select_from(BusinessOnboarding)) == 1
        content = session.get(ContentItem, first["content_id"])
        assert content is not None
        assert content.status.value == "PUBLISHED"
        assert content.publication_channel == "Instagram"
        asset = session.get(MediaAsset, first["media_asset_id"])
        assert asset is not None
        assert asset.processing_status == "READY"
        assert asset.storage_provider == "memory"
        assert not asset.object_key.startswith(("http://", "https://"))
        stored_bytes, stored_mime = storage.objects[asset.object_key]
        assert stored_mime == "image/png"
        assert asset.byte_size == len(stored_bytes)
        assert asset.checksum_sha256 == sha256(stored_bytes).hexdigest()
        with Image.open(io.BytesIO(stored_bytes)) as image:
            assert image.format == "PNG"
            assert image.size == (1, 1)
            image.verify()
        pilot_assets = [
            session.get(MediaAsset, first["pilot_square_before_media_asset_id"]),
            session.get(MediaAsset, first["pilot_square_after_media_asset_id"]),
            session.get(MediaAsset, first["pilot_vertical_media_asset_id"]),
        ]
        assert all(item is not None for item in pilot_assets)
        typed_pilot_assets = [item for item in pilot_assets if item is not None]
        assert {(item.width, item.height) for item in typed_pilot_assets} == {
            (800, 800),
            (720, 1280),
        }
        assert len({item.checksum_sha256 for item in typed_pilot_assets}) == 3
        assert all(item.object_key in storage.objects for item in typed_pilot_assets)
        association = session.scalar(
            select(ContentVersionMedia).where(
                ContentVersionMedia.content_version_id == content.current_version_id,
                ContentVersionMedia.media_asset_id == asset.id,
            )
        )
        assert association is not None
        image_approval = session.scalar(
            select(Approval).where(
                Approval.content_item_id == content.id,
                Approval.content_version_id == content.current_version_id,
                Approval.component == ApprovalComponent.IMAGE,
            )
        )
        assert image_approval is not None
        assert association.content_version_id == image_approval.content_version_id
        client = session.scalar(select(User).where(User.email == "client@clinicafeliz.local"))
        assert client is not None
        admin = session.scalar(select(User).where(User.email == "admin@devmark.local"))
        assert admin is not None
        assert client.password_hash != admin.password_hash
        preference = session.scalar(
            select(NotificationPreference).where(NotificationPreference.user_id == admin.id)
        )
        assert preference is not None
        assert preference.revision == 1
        business = session.get(Business, first["business_id"])
        onboarding = session.get(BusinessOnboarding, first["onboarding_id"])
        assert business is not None
        assert onboarding is not None
        assert business.onboarding_status == "COMPLETED"
        assert onboarding.status == "COMPLETED"
        assert onboarding.completed_steps == list(range(1, 16))
        assert set(onboarding.step_data) == {str(step) for step in range(1, 16)}
        assert onboarding.step_data["13"]["mode"] == "IMMEDIATE"
        assert onboarding.step_data["15"]["confirmed"] is True
        brand = session.scalar(
            select(BrandProfile).where(BrandProfile.business_id == first["business_id"])
        )
        assert brand is not None
        assert brand.logo_media_asset_ids == [str(first["pilot_square_after_media_asset_id"])]
        assert set(brand.visual_reference_media_asset_ids) == {
            str(first["pilot_square_before_media_asset_id"]),
            str(first["pilot_vertical_media_asset_id"]),
        }


def test_seed_repairs_missing_demo_media_object_and_link() -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        first = seed_demo(session, storage=storage)
        asset = session.get(MediaAsset, first["media_asset_id"])
        assert asset is not None
        association = session.scalar(select(ContentVersionMedia))
        assert association is not None

        storage.objects.clear()
        asset.processing_status = "FAILED"
        session.delete(association)
        session.commit()

        second = seed_demo(session, storage=storage)

        assert second == first
        assert session.scalar(select(func.count()).select_from(MediaAsset)) == 4
        assert session.scalar(select(func.count()).select_from(ContentVersionMedia)) == 5
        repaired_asset = session.get(MediaAsset, first["media_asset_id"])
        assert repaired_asset is not None
        assert repaired_asset.processing_status == "READY"
        assert repaired_asset.object_key in storage.objects


def test_seed_upgrades_a_legacy_phase2_brand_without_overwriting_custom_values() -> None:
    settings = get_settings()
    slug = re.sub(r"[^a-z0-9]+", "-", settings.demo_organization_name.casefold()).strip("-")
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        organization = Organization(name=settings.demo_organization_name, slug=slug)
        session.add(organization)
        session.flush()
        business = Business(
            organization_id=organization.id,
            name="Clínica Veterinária Demo",
            segment="Clínica veterinária",
        )
        session.add(business)
        session.flush()
        admin = User(
            email=settings.demo_admin_email,
            name="Administrador legado",
            password_hash=hash_password(settings.demo_admin_password),
        )
        reviewer = User(
            email=settings.demo_client_email,
            name="Revisor legado",
            password_hash=hash_password(settings.demo_client_password),
        )
        session.add_all([admin, reviewer])
        session.flush()
        session.add_all(
            [
                Membership(
                    organization_id=organization.id,
                    user_id=admin.id,
                    role=Role.AGENCY_ADMIN,
                ),
                Membership(
                    organization_id=organization.id,
                    user_id=reviewer.id,
                    role=Role.CLIENT_REVIEWER,
                    business_id=business.id,
                ),
            ]
        )
        brand = BrandProfile(
            organization_id=organization.id,
            business_id=business.id,
            brand_name="Clínica Veterinária Demo",
            public_name="Nome customizado no legado",
            description="Descrição legada que não pode ser sobrescrita.",
            segment="Clínica veterinária",
            audience="Tutores de animais da região",
            primary_colors=["#1F7A6D", "#F4F1DE"],
            tone_of_voice="acolhedor, claro e responsável",
            calls_to_action=["Agende uma conversa com nossa equipe."],
            version=1,
        )
        session.add(brand)
        session.commit()

        result = seed_demo(session, storage=storage)

        session.refresh(brand)
        session.refresh(business)
        assert result["organization_id"] == organization.id
        assert brand.public_name == "Nome customizado no legado"
        assert brand.description == "Descrição legada que não pode ser sobrescrita."
        assert brand.secondary_colors == ["#FFFFFF", "#E9C46A"]
        assert brand.fonts == ["Inter", "Source Sans 3"]
        assert brand.forbidden_rules
        assert brand.logo_media_asset_ids
        assert brand.visual_reference_media_asset_ids
        assert brand.version == 2
        onboarding = session.get(BusinessOnboarding, result["onboarding_id"])
        assert onboarding is not None
        assert onboarding.status == "COMPLETED"
        assert business.onboarding_status == "COMPLETED"
        assert set(onboarding.step_data) == {str(step) for step in range(1, 16)}


def test_seed_preserves_brand_fields_deliberately_cleared_after_phase3_upgrade() -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        result = seed_demo(session, storage=storage)
        brand = session.scalar(
            select(BrandProfile).where(BrandProfile.business_id == result["business_id"])
        )
        assert brand is not None
        brand.logo_media_asset_ids = []
        brand.forbidden_rules = []
        brand.contacts = {}
        reviewer_membership = session.scalar(
            select(Membership).where(Membership.user_id == result["reviewer_user_id"])
        )
        assert reviewer_membership is not None
        assert reviewer_membership.professional_review_granted is True
        reviewer_membership.professional_review_granted = False
        preserved_version = brand.version
        session.commit()

        seed_demo(session, storage=storage)

        session.refresh(brand)
        assert brand.logo_media_asset_ids == []
        assert brand.forbidden_rules == []
        assert brand.contacts == {}
        assert brand.version == preserved_version
        session.refresh(reviewer_membership)
        assert reviewer_membership.professional_review_granted is False


def test_seed_never_overwrites_storage_when_a_reserved_key_is_not_seed_owned() -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        result = seed_demo(session, storage=storage)
        asset = session.get(MediaAsset, result["pilot_square_before_media_asset_id"])
        assert asset is not None
        sentinel = (b"arquivo-local-preservado", "application/octet-stream")
        storage.objects[asset.object_key] = sentinel
        asset.origin = "UPLOAD"
        asset.metadata_safe = {"owner": "user"}
        object_key = asset.object_key
        session.commit()

        with pytest.raises(RuntimeError, match="nenhum objeto foi sobrescrito"):
            seed_demo(session, storage=storage)
        session.rollback()

        preserved = session.get(MediaAsset, asset.id)
        assert preserved is not None
        assert preserved.origin == "UPLOAD"
        assert preserved.metadata_safe == {"owner": "user"}
        assert storage.objects[object_key] == sentinel


def test_seed_preserves_later_versions_decisions_and_repairs_only_missing_links() -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        first = seed_demo(session, storage=storage)
        revised = session.get(ContentItem, first["revised_content_id"])
        assert revised is not None
        version_two = session.get(ContentVersion, revised.current_version_id)
        assert version_two is not None
        version_three = _append_content_revision(session, revised, version_two)
        revised.status = ContentStatus.INTERNAL_REVIEW
        preserved_approval = session.scalar(
            select(Approval).where(
                Approval.content_item_id == revised.id,
                Approval.component == ApprovalComponent.TEXT,
            )
        )
        assert preserved_approval is not None
        preserved_approval.decision_comment = "Decisão histórica preservada"

        changes = session.get(ContentItem, first["changes_requested_content_id"])
        assert changes is not None
        changes_entry = session.get(CalendarEntry, changes.calendar_entry_id)
        assert changes_entry is not None
        expected_changes_version = session.scalar(
            select(ContentVersion).where(
                ContentVersion.content_item_id == changes.id,
                ContentVersion.version_number == 1,
            )
        )
        assert expected_changes_version is not None
        changes.current_version_id = None
        changes_entry.content_item_id = None
        session.commit()

        second = seed_demo(session, storage=storage)

        session.refresh(revised)
        session.refresh(preserved_approval)
        session.refresh(changes)
        session.refresh(changes_entry)
        assert second == first
        assert revised.current_version_id == version_three.id
        assert revised.status == ContentStatus.INTERNAL_REVIEW
        assert preserved_approval.decision_comment == "Decisão histórica preservada"
        assert changes.current_version_id == expected_changes_version.id
        assert changes_entry.content_item_id == changes.id


def test_seed_repairs_notification_classification_without_resetting_read_state() -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        result = seed_demo(session, storage=storage)
        notifications = list(session.scalars(select(Notification)).all())
        read_at = datetime(2026, 1, 2, 12, tzinfo=UTC)
        for notification in notifications:
            notification.category = NotificationCategory.REPORT_AVAILABLE
            notification.importance = NotificationImportance.NORMAL
            notification.read_at = read_at
        session.commit()

        seed_demo(session, storage=storage)

        expected = {
            result["content_id"]: (
                NotificationCategory.CONTENT_APPROVED,
                NotificationImportance.NORMAL,
            ),
            result["changes_requested_content_id"]: (
                NotificationCategory.CONTENT_CHANGES_REQUESTED,
                NotificationImportance.NORMAL,
            ),
            result["review_content_id"]: (
                NotificationCategory.CONTENT_AWAITING_APPROVAL,
                NotificationImportance.URGENT,
            ),
        }
        repaired = list(session.scalars(select(Notification)).all())
        assert len(repaired) == 3
        for notification in repaired:
            assert notification.resource_id is not None
            assert (notification.category, notification.importance) == expected[
                notification.resource_id
            ]
            assert notification.read_at == read_at


def test_seed_refuses_to_adopt_an_unrelated_strategy_version_two() -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        result = seed_demo(session, storage=storage)
        version_two = session.get(StrategyVersion, result["strategy_version_id"])
        assert version_two is not None
        version_two.provider_reference = "versao-criada-pelo-usuario"
        session.commit()

        with pytest.raises(RuntimeError, match=r"versão 2.*não foi criada"):
            seed_demo(session, storage=storage)


def test_seed_refuses_to_append_to_a_manual_strategy_version_one() -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        result = seed_demo(session, storage=storage)
        strategy = session.get(ContentStrategy, result["strategy_id"])
        pilot_version = session.get(StrategyVersion, result["strategy_version_id"])
        plan = session.get(ContentPlan, result["content_plan_id"])
        assert strategy is not None
        assert pilot_version is not None
        assert plan is not None
        first_version = session.scalar(
            select(StrategyVersion).where(
                StrategyVersion.content_strategy_id == strategy.id,
                StrategyVersion.version_number == 1,
            )
        )
        assert first_version is not None
        strategy.current_version_id = first_version.id
        strategy.approved_version_id = first_version.id
        plan.strategy_version_id = first_version.id
        for content in session.scalars(
            select(ContentItem).where(ContentItem.content_strategy_id == strategy.id)
        ):
            content.strategy_version_id = first_version.id
        session.flush()
        session.delete(pilot_version)
        first_version.source = "MANUAL"
        first_version.provider_name = "manual"
        first_version.provider_reference = "versao-criada-pelo-usuario"
        session.commit()

        with pytest.raises(RuntimeError, match=r"versão inicial.*não foi criada"):
            seed_demo(session, storage=storage)
        session.rollback()

        assert (
            session.scalar(
                select(func.count())
                .select_from(StrategyVersion)
                .where(StrategyVersion.content_strategy_id == strategy.id)
            )
            == 1
        )
        session.refresh(strategy)
        assert strategy.current_version_id == first_version.id
        assert strategy.approved_version_id == first_version.id


def test_seed_does_not_touch_another_tenant_with_identical_catalog_names() -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        other_organization = Organization(name="Outra organização", slug="outra-organizacao")
        session.add(other_organization)
        session.flush()
        other_business = Business(
            organization_id=other_organization.id,
            name="Clínica Veterinária Demo",
            segment="Outro segmento preservado",
        )
        other_user = User(
            email="admin@outro-tenant.example",
            name="Outro administrador",
            password_hash=hash_password("senha-ficticia-outro-tenant"),
        )
        session.add_all([other_business, other_user])
        session.flush()
        session.add(
            Membership(
                organization_id=other_organization.id,
                user_id=other_user.id,
                role=Role.AGENCY_ADMIN,
            )
        )
        other_brand = BrandProfile(
            organization_id=other_organization.id,
            business_id=other_business.id,
            brand_name="Clínica Veterinária Demo",
            public_name="Marca do outro tenant",
        )
        session.add(other_brand)
        session.flush()
        other_service = Service(
            organization_id=other_organization.id,
            business_id=other_business.id,
            name="Consulta preventiva",
            description="Não alterar este registro",
        )
        other_audience = AudienceSegment(
            organization_id=other_organization.id,
            business_id=other_business.id,
            name="Tutores de primeira viagem",
            description="Público do outro tenant",
        )
        other_objective = MarketingObjective(
            organization_id=other_organization.id,
            business_id=other_business.id,
            name="Educação preventiva",
            description="Objetivo do outro tenant",
        )
        other_preset = VisualPreset(
            organization_id=other_organization.id,
            business_id=other_business.id,
            brand_profile_id=other_brand.id,
            name="Feed educativo acolhedor",
            format="Feed",
            aspect_ratio="1:1",
            creation_mode="MANUAL",
            created_by_user_id=other_user.id,
            updated_by_user_id=other_user.id,
        )
        session.add_all([other_service, other_audience, other_objective, other_preset])
        session.commit()
        untouched_ids = {
            other_service.id,
            other_audience.id,
            other_objective.id,
            other_preset.id,
        }

        result = seed_demo(session, storage=storage)

        session.refresh(other_business)
        session.refresh(other_brand)
        session.refresh(other_service)
        session.refresh(other_audience)
        session.refresh(other_objective)
        session.refresh(other_preset)
        assert result["organization_id"] != other_organization.id
        assert other_business.segment == "Outro segmento preservado"
        assert other_brand.public_name == "Marca do outro tenant"
        assert other_service.description == "Não alterar este registro"
        assert other_audience.description == "Público do outro tenant"
        assert other_objective.description == "Objetivo do outro tenant"
        assert other_preset.creation_mode == "MANUAL"
        assert untouched_ids == {
            other_service.id,
            other_audience.id,
            other_objective.id,
            other_preset.id,
        }


def test_seed_builds_a_safe_and_report_ready_veterinary_pilot() -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        result = seed_demo(session, storage=storage)

        strategy_versions = list(
            session.scalars(select(StrategyVersion).order_by(StrategyVersion.version_number)).all()
        )
        assert [version.version_number for version in strategy_versions] == [1, 2]
        assert strategy_versions[1].supersedes_version_id == strategy_versions[0].id
        assert strategy_versions[1].provider_name == "mock"
        assert len(strategy_versions[1].service_snapshots) == 3
        assert len(strategy_versions[1].audience_snapshots) == 3
        assert len(strategy_versions[1].objective_snapshots) == 3

        sensitive = session.get(ContentItem, result["sensitive_content_id"])
        assert sensitive is not None
        assert sensitive.status == ContentStatus.CLIENT_REVIEW
        sensitive_version = session.get(ContentVersion, sensitive.current_version_id)
        assert sensitive_version is not None
        assert "CONTEÚDO VETERINÁRIO SENSÍVEL" in sensitive_version.caption
        assert "REVISÃO PROFISSIONAL OBRIGATÓRIA" in sensitive_version.caption
        assert "não deve ser publicado" in sensitive_version.caption
        assert sensitive_version.provider_name == "mock"
        assert sensitive_version.is_sensitive is True
        assert sensitive_version.sensitivity_score >= 50
        assert sensitive_version.sensitivity_categories
        assert sensitive_version.sensitivity_codes
        assert sensitive_version.sensitivity_provider == ("contextual_rules+mock_veterinary_safety")
        assert (
            session.scalar(
                select(func.count())
                .select_from(Approval)
                .where(Approval.content_item_id == sensitive.id)
            )
            == 2
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(ContentVersionMedia)
                .where(ContentVersionMedia.content_version_id == sensitive_version.id)
            )
            == 0
        )

        changes = session.get(ContentItem, result["changes_requested_content_id"])
        assert changes is not None
        assert changes.status == ContentStatus.CHANGES_REQUESTED
        change_decisions: dict[ApprovalComponent, ApprovalStatus] = dict(
            session.execute(
                select(Approval.component, Approval.status).where(
                    Approval.content_item_id == changes.id
                )
            )
            .tuples()
            .all()
        )
        assert change_decisions == {
            ApprovalComponent.TEXT: ApprovalStatus.CHANGES_REQUESTED,
            ApprovalComponent.IMAGE: ApprovalStatus.APPROVED,
        }

        revised = session.get(ContentItem, result["revised_content_id"])
        assert revised is not None
        assert revised.status == ContentStatus.DRAFT
        revised_versions = list(
            session.scalars(
                select(ContentVersion)
                .where(ContentVersion.content_item_id == revised.id)
                .order_by(ContentVersion.version_number)
            ).all()
        )
        assert [version.version_number for version in revised_versions] == [1, 2]
        assert revised.current_version_id == revised_versions[1].id
        assert revised_versions[1].provider_name == "manual_revision"
        revised_media = dict(
            session.execute(
                select(
                    ContentVersionMedia.content_version_id,
                    ContentVersionMedia.media_asset_id,
                ).where(
                    ContentVersionMedia.content_version_id.in_(
                        [version.id for version in revised_versions]
                    ),
                    ContentVersionMedia.role == "PRIMARY",
                )
            )
            .tuples()
            .all()
        )
        assert revised_media == {
            revised_versions[0].id: result["pilot_square_before_media_asset_id"],
            revised_versions[1].id: result["pilot_square_after_media_asset_id"],
        }

        review = session.get(ContentItem, result["review_content_id"])
        assert review is not None
        assert review.status == ContentStatus.CLIENT_REVIEW
        assert set(
            session.scalars(
                select(Approval.status).where(Approval.content_item_id == review.id)
            ).all()
        ) == {ApprovalStatus.PENDING}


def test_seed_sensitive_fixture_blocks_common_approval_without_professional_review(
    client: TestClient,
) -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        result = seed_demo(session, storage=storage)

    settings = get_settings()
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.demo_client_email,
            "password": settings.demo_client_password,
        },
    )
    assert login.status_code == 200, login.text
    csrf = login.json()["csrf_token"]
    blocked = client.post(
        f"/api/v1/contents/{result['sensitive_content_id']}/decisions/TEXT/approve",
        json={"comment": "Tentativa antes da revisão profissional"},
        headers=csrf_headers(csrf),
    )
    assert blocked.status_code == 409, blocked.text
    assert "aprovação profissional" in blocked.json()["detail"].lower()


def test_seed_period_is_visible_in_the_real_report_endpoint(client: TestClient) -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        result = seed_demo(session, storage=storage)
        strategy = session.get(ContentStrategy, result["strategy_id"])
        assert strategy is not None
        starts_on = strategy.starts_on
        ends_on = strategy.ends_on

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@devmark.local",
            "password": "local-demo-only-change-before-use",
        },
    )
    assert login.status_code == 200, login.text

    onboarding_response = client.get(f"/api/v1/businesses/{result['business_id']}/onboarding")
    assert onboarding_response.status_code == 200, onboarding_response.text
    onboarding_payload = onboarding_response.json()
    assert onboarding_payload["status"] == "COMPLETED"
    assert onboarding_payload["progress_percent"] == 100
    assert onboarding_payload["missing_steps"] == []

    report_response = client.get(
        f"/api/v1/businesses/{result['business_id']}/reports/period",
        params={"starts_on": starts_on.isoformat(), "ends_on": ends_on.isoformat()},
    )
    assert report_response.status_code == 200, report_response.text
    report = report_response.json()
    assert report["content_total"] == 5
    assert report["content_by_status"]["PUBLISHED"] == 1
    assert report["content_by_status"]["CHANGES_REQUESTED"] == 1
    assert report["content_by_status"]["CLIENT_REVIEW"] == 2
    assert report["content_by_status"]["DRAFT"] == 1
    assert report["content_versions_total"] == 6
    assert report["revisions_total"] == 1
    assert report["manual_publications_total"] == 1
    assert report["publications_by_channel"] == {"Instagram": 1}
    assert report["strategies_total"] == 1
    assert report["approved_strategies_total"] == 1
    assert report["calendar_entries_total"] == 5
    assert "impressoes" in report["unavailable_metrics"]
