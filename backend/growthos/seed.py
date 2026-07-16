import re
from base64 import b64decode
from calendar import monthrange
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.config import get_settings
from growthos.database import get_session_factory
from growthos.domain.enums import (
    ApprovalComponent,
    ApprovalStage,
    ApprovalStatus,
    ContentStatus,
    Role,
)
from growthos.models import (
    Approval,
    AudienceSegment,
    BrandProfile,
    Business,
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
    Organization,
    Service,
    StrategyVersion,
    User,
    VisualPreset,
)
from growthos.security import hash_password, normalize_email
from growthos.services.storage import StorageProvider, get_storage_provider, validate_image_upload

_PHASE2_DEMO_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    validate=True,
)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "devmark-demo"


def _get_or_create_user(session: Session, email: str, name: str, password: str) -> User:
    normalized = normalize_email(email)
    user = session.scalar(select(User).where(User.email == normalized))
    if user is None:
        user = User(
            email=normalized,
            name=name,
            password_hash=hash_password(password),
            is_active=True,
        )
        session.add(user)
        session.flush()
    return user


def _month_period(reference: date) -> tuple[date, date]:
    starts_on = reference.replace(day=1)
    ends_on = reference.replace(day=monthrange(reference.year, reference.month)[1])
    return starts_on, ends_on


def _ensure_phase2_demo_media(
    session: Session,
    *,
    organization: Organization,
    business: Business,
    content: ContentItem,
    admin: User,
    storage: StorageProvider,
) -> MediaAsset:
    """Keep the published demo and every image review backed by private media."""
    current_version_id = content.current_version_id
    if current_version_id is None:
        raise RuntimeError("Conteúdo demo publicado sem versão atual")

    version_ids = set(
        session.scalars(
            select(Approval.content_version_id).where(
                Approval.organization_id == organization.id,
                Approval.business_id == business.id,
                Approval.content_item_id == content.id,
                Approval.component == ApprovalComponent.IMAGE,
            )
        ).all()
    )
    version_ids.add(current_version_id)
    scoped_version_ids = set(
        session.scalars(
            select(ContentVersion.id).where(
                ContentVersion.id.in_(version_ids),
                ContentVersion.organization_id == organization.id,
                ContentVersion.business_id == business.id,
                ContentVersion.content_item_id == content.id,
            )
        ).all()
    )
    if scoped_version_ids != version_ids:
        raise RuntimeError("Conteúdo demo possui aprovação visual sem versão válida")

    validated = validate_image_upload(
        _PHASE2_DEMO_PNG,
        declared_mime="image/png",
        allowed_mime_types=frozenset({"image/png"}),
        max_bytes=1024 * 1024,
    )
    object_key = (
        f"organizations/{organization.id}/businesses/{business.id}/media/seed/phase2-demo.png"
    )
    storage.put(object_key, validated.data, validated.mime_type)

    asset = session.scalar(
        select(MediaAsset).where(
            MediaAsset.organization_id == organization.id,
            MediaAsset.business_id == business.id,
            MediaAsset.object_key == object_key,
        )
    )
    if asset is None:
        asset = MediaAsset(
            organization_id=organization.id,
            business_id=business.id,
            kind="IMAGE",
            storage_provider=storage.name,
            object_key=object_key,
            display_name="imagem-demo-fase-2.png",
            mime_type=validated.mime_type,
            byte_size=validated.byte_size,
            checksum_sha256=validated.checksum_sha256,
            width=validated.width,
            height=validated.height,
            origin="SEED",
            processing_status="READY",
            metadata_safe={"fixture": "phase2-demo"},
            created_by_user_id=admin.id,
        )
        session.add(asset)
        session.flush()
    else:
        asset.kind = "IMAGE"
        asset.storage_provider = storage.name
        asset.display_name = "imagem-demo-fase-2.png"
        asset.mime_type = validated.mime_type
        asset.byte_size = validated.byte_size
        asset.checksum_sha256 = validated.checksum_sha256
        asset.width = validated.width
        asset.height = validated.height
        asset.origin = "SEED"
        asset.processing_status = "READY"
        asset.metadata_safe = {"fixture": "phase2-demo"}
        asset.archived_at = None

    for version_id in sorted(version_ids, key=str):
        association = session.scalar(
            select(ContentVersionMedia).where(
                ContentVersionMedia.organization_id == organization.id,
                ContentVersionMedia.business_id == business.id,
                ContentVersionMedia.content_version_id == version_id,
                ContentVersionMedia.media_asset_id == asset.id,
                ContentVersionMedia.role == "PRIMARY",
            )
        )
        if association is None:
            session.add(
                ContentVersionMedia(
                    organization_id=organization.id,
                    business_id=business.id,
                    content_version_id=version_id,
                    media_asset_id=asset.id,
                    role="PRIMARY",
                    sort_order=0,
                    created_by_user_id=admin.id,
                )
            )
    return asset


def _seed_phase2_demo(
    session: Session,
    *,
    organization: Organization,
    business: Business,
    brand: BrandProfile,
    admin: User,
    reviewer: User,
    storage: StorageProvider,
) -> dict[str, UUID]:
    service = session.scalar(
        select(Service).where(
            Service.organization_id == organization.id,
            Service.business_id == business.id,
            Service.name == "Consulta preventiva",
        )
    )
    if service is None:
        service = Service(
            organization_id=organization.id,
            business_id=business.id,
            name="Consulta preventiva",
            description="Avaliação fictícia de rotina para cães e gatos.",
            category="Prevenção",
            warnings=["Conteúdo educativo; não substitui avaliação veterinária."],
        )
        session.add(service)
        session.flush()

    audience = session.scalar(
        select(AudienceSegment).where(
            AudienceSegment.organization_id == organization.id,
            AudienceSegment.business_id == business.id,
            AudienceSegment.name == "Tutores de primeira viagem",
        )
    )
    if audience is None:
        audience = AudienceSegment(
            organization_id=organization.id,
            business_id=business.id,
            name="Tutores de primeira viagem",
            description="Pessoas que adotaram seu primeiro animal recentemente.",
            needs=["orientação simples", "rotina preventiva"],
            objections=["receio de custos inesperados"],
            location="Região da clínica demo",
        )
        session.add(audience)
        session.flush()

    objective = session.scalar(
        select(MarketingObjective).where(
            MarketingObjective.organization_id == organization.id,
            MarketingObjective.business_id == business.id,
            MarketingObjective.name == "Educação preventiva",
        )
    )
    if objective is None:
        objective = MarketingObjective(
            organization_id=organization.id,
            business_id=business.id,
            name="Educação preventiva",
            description="Ajudar tutores a reconhecer o valor do cuidado recorrente.",
            planned_indicators=["conteúdos aprovados", "publicações registradas"],
        )
        session.add(objective)
        session.flush()

    preset = session.scalar(
        select(VisualPreset).where(
            VisualPreset.organization_id == organization.id,
            VisualPreset.business_id == business.id,
            VisualPreset.name == "Feed educativo acolhedor",
        )
    )
    if preset is None:
        preset = VisualPreset(
            organization_id=organization.id,
            business_id=business.id,
            brand_profile_id=brand.id,
            name="Feed educativo acolhedor",
            objective="Explicar prevenção com clareza e proximidade.",
            format="Feed",
            aspect_ratio="1:1",
            creation_mode="HYBRID",
            color_palette=["#1F7A6D", "#F4F1DE", "#FFFFFF"],
            fonts=["Inter", "Source Sans 3"],
            logo_position="inferior direito",
            logo_scale_percent=16,
            safe_margins={"top": 8, "right": 8, "bottom": 8, "left": 8},
            background_style="formas orgânicas claras e discretas",
            photographic_style="fotografia documental acolhedora",
            realism_level="natural",
            lighting="luz natural suave",
            composition="animal e tutor em primeiro plano, com espaço para título",
            max_text_characters=90,
            text_rules=["uma ideia principal", "alto contraste", "sem texto clínico sensível"],
            base_prompt="Cena veterinária responsável, humana e educativa.",
            negative_prompt="sem diagnóstico, sem procedimento invasivo, sem texto ilegível",
            allowed_elements=["tutor", "animal saudável", "ambiente limpo"],
            forbidden_elements=["sangue", "medicação", "promessa de cura"],
            visual_signature="verde profundo, creme e enquadramento humano",
            default_cta="Agende uma conversa com nossa equipe.",
            created_by_user_id=admin.id,
            updated_by_user_id=admin.id,
        )
        session.add(preset)
        session.flush()

    starts_on, ends_on = _month_period(datetime.now(UTC).date())
    period_key = starts_on.strftime("%Y-%m")
    strategy = session.scalar(
        select(ContentStrategy).where(
            ContentStrategy.organization_id == organization.id,
            ContentStrategy.business_id == business.id,
            ContentStrategy.name == "Estratégia mensal demo",
            ContentStrategy.starts_on == starts_on,
            ContentStrategy.ends_on == ends_on,
        )
    )
    if strategy is None:
        strategy = ContentStrategy(
            organization_id=organization.id,
            business_id=business.id,
            name="Estratégia mensal demo",
            starts_on=starts_on,
            ends_on=ends_on,
            status="APPROVED",
            created_by_user_id=admin.id,
            submitted_by_user_id=admin.id,
            submitted_at=datetime.now(UTC),
            decided_by_user_id=reviewer.id,
            decided_at=datetime.now(UTC),
            decision_comment="Direção fictícia aprovada para demonstração.",
        )
        session.add(strategy)
        session.flush()
        strategy_version = StrategyVersion(
            organization_id=organization.id,
            business_id=business.id,
            content_strategy_id=strategy.id,
            version_number=1,
            objective="Ensinar cuidados preventivos de forma simples e responsável.",
            positioning="A clínica próxima que orienta antes de qualquer decisão.",
            funnel=["descoberta", "educação", "conversa"],
            channels=["Instagram"],
            pillars=[
                {"name": "Prevenção", "description": "Hábitos e consultas de rotina"},
                {"name": "Acolhimento", "description": "Relação entre tutor, animal e equipe"},
            ],
            planned_indicators=["conteúdos aprovados", "publicações registradas"],
            service_snapshots=[{"id": str(service.id), "name": service.name}],
            audience_snapshots=[{"id": str(audience.id), "name": audience.name}],
            objective_snapshots=[{"id": str(objective.id), "name": objective.name}],
            brand_context_snapshot={
                "brand_name": brand.brand_name,
                "tone_of_voice": brand.tone_of_voice,
                "primary_colors": list(brand.primary_colors),
            },
            source="MOCK",
            provider_name="mock",
            provider_reference="seed-phase2-v1",
            created_by_user_id=admin.id,
        )
        session.add(strategy_version)
        session.flush()
        strategy.current_version_id = strategy_version.id
        strategy.approved_version_id = strategy_version.id
    else:
        existing_strategy_version = session.scalar(
            select(StrategyVersion).where(
                StrategyVersion.id == strategy.current_version_id,
                StrategyVersion.organization_id == organization.id,
                StrategyVersion.business_id == business.id,
            )
        )
        if existing_strategy_version is None:
            raise RuntimeError("Estratégia demo existente sem versão atual válida")
        strategy_version = existing_strategy_version

    plan = session.scalar(
        select(ContentPlan).where(
            ContentPlan.organization_id == organization.id,
            ContentPlan.business_id == business.id,
            ContentPlan.name == "Calendário editorial demo",
            ContentPlan.starts_on == starts_on,
            ContentPlan.ends_on == ends_on,
        )
    )
    if plan is None:
        plan = ContentPlan(
            organization_id=organization.id,
            business_id=business.id,
            content_strategy_id=strategy.id,
            strategy_version_id=strategy_version.id,
            name="Calendário editorial demo",
            starts_on=starts_on,
            ends_on=ends_on,
            frequency="SEMANAL",
            status="ACTIVE",
            created_by_user_id=admin.id,
        )
        session.add(plan)
        session.flush()

    suggested_for = datetime(
        starts_on.year,
        starts_on.month,
        min(15, ends_on.day),
        14,
        tzinfo=UTC,
    )
    calendar_entry = session.scalar(
        select(CalendarEntry).where(
            CalendarEntry.organization_id == organization.id,
            CalendarEntry.business_id == business.id,
            CalendarEntry.content_plan_id == plan.id,
            CalendarEntry.title == "Checklist preventivo do mês",
            CalendarEntry.suggested_for == suggested_for,
        )
    )
    if calendar_entry is None:
        calendar_entry = CalendarEntry(
            organization_id=organization.id,
            business_id=business.id,
            content_plan_id=plan.id,
            visual_preset_id=preset.id,
            title="Checklist preventivo do mês",
            objective=objective.description,
            audience=audience.name,
            channel="Instagram",
            format="Feed",
            suggested_for=suggested_for,
            status="PUBLISHED",
            notes="Pauta fictícia criada pelo seed da Fase 2.",
            sort_order=0,
            created_by_user_id=admin.id,
        )
        session.add(calendar_entry)
        session.flush()

    content = session.scalar(
        select(ContentItem).where(
            ContentItem.organization_id == organization.id,
            ContentItem.business_id == business.id,
            ContentItem.calendar_entry_id == calendar_entry.id,
        )
    )
    if content is None:
        content = ContentItem(
            organization_id=organization.id,
            business_id=business.id,
            status=ContentStatus.PUBLISHED,
            content_strategy_id=strategy.id,
            strategy_version_id=strategy_version.id,
            content_plan_id=plan.id,
            calendar_entry_id=calendar_entry.id,
            visual_preset_id=preset.id,
            scheduled_for=suggested_for,
            published_at=suggested_for,
            publication_channel="Instagram",
            publication_reference="https://example.invalid/publicacao-demo",
            published_by_user_id=admin.id,
            publication_idempotency_key=f"seed-phase2-publication-{period_key}",
            created_by_user_id=admin.id,
        )
        session.add(content)
        session.flush()
        content_version = ContentVersion(
            organization_id=organization.id,
            business_id=business.id,
            content_item_id=content.id,
            version_number=1,
            title="Checklist preventivo do mês",
            caption=(
                "Uma rotina preventiva ajuda a observar mudanças com calma. "
                "Converse com a equipe veterinária sobre o cuidado adequado ao seu animal."
            ),
            channel="Instagram",
            format="Feed",
            objective=objective.description,
            audience=audience.name,
            cta=preset.default_cta,
            service_id=service.id,
            audience_segment_id=audience.id,
            marketing_objective_id=objective.id,
            notes="Conteúdo inteiramente fictício para demonstração local.",
            script="Apresente três hábitos preventivos e encerre com orientação profissional.",
            visual_prompt=(
                "[mock] Cena veterinária responsável, humana e educativa; "
                "luz natural suave; proporção 1:1."
            ),
            negative_prompt=preset.negative_prompt,
            brand_context_snapshot={
                "brand_name": brand.brand_name,
                "tone_of_voice": brand.tone_of_voice,
            },
            visual_preset_snapshot={
                "id": str(preset.id),
                "name": preset.name,
                "version": preset.version,
                "provider": "mock",
            },
            provider_name="mock",
            created_by_user_id=admin.id,
        )
        session.add(content_version)
        session.flush()
        content.current_version_id = content_version.id
        calendar_entry.content_item_id = content.id
        for component in ApprovalComponent:
            session.add(
                Approval(
                    organization_id=organization.id,
                    business_id=business.id,
                    content_item_id=content.id,
                    content_version_id=content_version.id,
                    stage=ApprovalStage.CLIENT,
                    component=component,
                    status=ApprovalStatus.APPROVED,
                    requested_by_user_id=admin.id,
                    decided_by_user_id=reviewer.id,
                    decision_comment="Componente fictício aprovado no seed.",
                    decided_at=suggested_for,
                )
            )
        session.add(
            Notification(
                organization_id=organization.id,
                business_id=business.id,
                recipient_user_id=admin.id,
                type="CONTENT_DECISION",
                title="Conteúdo demo aprovado",
                message="Texto e imagem do conteúdo fictício foram aprovados.",
                resource_type="content_item",
                resource_id=content.id,
                created_at=suggested_for,
            )
        )

    media_asset = _ensure_phase2_demo_media(
        session,
        organization=organization,
        business=business,
        content=content,
        admin=admin,
        storage=storage,
    )

    return {
        "service_id": service.id,
        "audience_id": audience.id,
        "objective_id": objective.id,
        "visual_preset_id": preset.id,
        "strategy_id": strategy.id,
        "strategy_version_id": strategy_version.id,
        "content_plan_id": plan.id,
        "calendar_entry_id": calendar_entry.id,
        "content_id": content.id,
        "media_asset_id": media_asset.id,
    }


def seed_demo(
    session: Session,
    *,
    storage: StorageProvider | None = None,
) -> dict[str, UUID]:
    settings = get_settings()
    settings.ensure_demo_seed_allowed()
    selected_storage = storage if storage is not None else get_storage_provider(settings)
    slug = _slugify(settings.demo_organization_name)
    organization = session.scalar(select(Organization).where(Organization.slug == slug))
    if organization is None:
        organization = Organization(name=settings.demo_organization_name, slug=slug)
        session.add(organization)
        session.flush()

    business = session.scalar(
        select(Business).where(
            Business.organization_id == organization.id,
            Business.name == "Clínica Veterinária Demo",
        )
    )
    if business is None:
        business = Business(
            organization_id=organization.id,
            name="Clínica Veterinária Demo",
            segment="Clínica veterinária",
        )
        session.add(business)
        session.flush()

    admin = _get_or_create_user(
        session,
        settings.demo_admin_email,
        "Administrador DevMark Demo",
        settings.demo_admin_password,
    )
    reviewer = _get_or_create_user(
        session,
        settings.demo_client_email,
        "Revisor Cliente Demo",
        settings.demo_client_password,
    )

    memberships = [
        (admin, Role.AGENCY_ADMIN, None),
        (reviewer, Role.CLIENT_REVIEWER, business.id),
    ]
    for user, role, business_id in memberships:
        membership = session.scalar(
            select(Membership).where(
                Membership.organization_id == organization.id,
                Membership.user_id == user.id,
            )
        )
        if membership is None:
            session.add(
                Membership(
                    organization_id=organization.id,
                    user_id=user.id,
                    role=role,
                    business_id=business_id,
                )
            )

    brand = session.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == organization.id,
            BrandProfile.business_id == business.id,
        )
    )
    if brand is None:
        brand = BrandProfile(
            organization_id=organization.id,
            business_id=business.id,
            brand_name="Clínica Veterinária Demo",
            public_name="Vet Demo",
            description="Dados inteiramente fictícios para desenvolvimento local.",
            segment="Clínica veterinária",
            audience="Tutores de animais da região",
            primary_colors=["#1F7A6D", "#F4F1DE"],
            tone_of_voice="acolhedor, claro e responsável",
            calls_to_action=["Agende uma conversa com nossa equipe."],
        )
        session.add(brand)
        session.flush()
    phase2 = _seed_phase2_demo(
        session,
        organization=organization,
        business=business,
        brand=brand,
        admin=admin,
        reviewer=reviewer,
        storage=selected_storage,
    )
    session.commit()
    return {
        "organization_id": organization.id,
        "business_id": business.id,
        "admin_user_id": admin.id,
        "reviewer_user_id": reviewer.id,
        **phase2,
    }


def main() -> None:
    with get_session_factory()() as session:
        result = seed_demo(session)
    print("Seed demo concluído:", result)


if __name__ == "__main__":
    main()
