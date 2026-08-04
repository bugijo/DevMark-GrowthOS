import re
from base64 import b64decode
from calendar import monthrange
from datetime import UTC, date, datetime, time
from io import BytesIO
from typing import Any
from uuid import UUID

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.config import get_settings
from growthos.database import get_session_factory
from growthos.domain.enums import (
    ApprovalComponent,
    ApprovalStage,
    ApprovalStatus,
    ContentStatus,
    NotificationCategory,
    NotificationDeliveryMode,
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
    NotificationPreference,
    Organization,
    Service,
    StrategyVersion,
    User,
    VisualPreset,
)
from growthos.schemas_notifications import (
    NotificationCategoryPreferenceInput,
    NotificationPreferenceUpdate,
)
from growthos.security import hash_password, normalize_email
from growthos.services.audit import add_audit_log
from growthos.services.notification_preferences import upsert_notification_preference
from growthos.services.sensitivity import (
    VeterinarySensitivityClassifier,
    assessment_fields,
    content_document,
)
from growthos.services.storage import StorageProvider, get_storage_provider, validate_image_upload

_PHASE2_DEMO_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    validate=True,
)

_PILOT_SENSITIVE_MARKER = (
    "[RASCUNHO INTERNO — CONTEÚDO VETERINÁRIO SENSÍVEL — REVISÃO PROFISSIONAL OBRIGATÓRIA]"
)
_PILOT_STRATEGY_REFERENCE = "seed-phase3-pilot-v2"


def _assess_seed_content_version(version: ContentVersion) -> None:
    assessment = VeterinarySensitivityClassifier().assess(
        content_document(
            title=version.title,
            caption=version.caption,
            objective=version.objective,
            audience=version.audience,
            cta=version.cta,
            notes=version.notes,
            script=version.script,
            visual_prompt=version.visual_prompt,
            negative_prompt=version.negative_prompt,
        )
    )
    for field, value in assessment_fields(assessment).items():
        setattr(version, field, value)


def _render_pilot_image(
    *,
    width: int,
    height: int,
    background: str,
    accent: str,
    secondary: str,
    variant: int,
) -> bytes:
    """Render a small deterministic, fictional visual without external assets."""

    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    margin = max(24, min(width, height) // 12)
    draw.rounded_rectangle(
        (margin, margin, width - margin, height - margin),
        radius=max(20, margin // 2),
        fill=secondary,
        outline=accent,
        width=max(6, margin // 8),
    )
    center_x = width // 2
    center_y = height // 2 + (variant - 1) * max(8, height // 40)
    paw_radius = max(24, min(width, height) // 12)
    draw.ellipse(
        (
            center_x - paw_radius,
            center_y - paw_radius // 2,
            center_x + paw_radius,
            center_y + paw_radius * 3 // 2,
        ),
        fill=accent,
    )
    toe_radius = max(12, paw_radius // 3)
    for offset_x, offset_y in (
        (-paw_radius, -paw_radius),
        (-paw_radius // 3, -paw_radius * 3 // 2),
        (paw_radius // 3, -paw_radius * 3 // 2),
        (paw_radius, -paw_radius),
    ):
        draw.ellipse(
            (
                center_x + offset_x - toe_radius,
                center_y + offset_y - toe_radius,
                center_x + offset_x + toe_radius,
                center_y + offset_y + toe_radius,
            ),
            fill=accent,
        )
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _pilot_media_payloads() -> tuple[tuple[str, str, bytes], ...]:
    return (
        (
            "phase3-pilot-square-before",
            "piloto-feed-versao-1.png",
            _render_pilot_image(
                width=800,
                height=800,
                background="#F4F1DE",
                accent="#1F7A6D",
                secondary="#FFFFFF",
                variant=1,
            ),
        ),
        (
            "phase3-pilot-square-after",
            "piloto-feed-versao-2.png",
            _render_pilot_image(
                width=800,
                height=800,
                background="#EAF4F1",
                accent="#145C52",
                secondary="#FFF8D6",
                variant=2,
            ),
        ),
        (
            "phase3-pilot-vertical",
            "piloto-stories.png",
            _render_pilot_image(
                width=720,
                height=1280,
                background="#F4F1DE",
                accent="#1F7A6D",
                secondary="#FFFFFF",
                variant=3,
            ),
        ),
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


def _ensure_pilot_media_assets(
    session: Session,
    *,
    organization: Organization,
    business: Business,
    admin: User,
    storage: StorageProvider,
) -> dict[str, MediaAsset]:
    assets: dict[str, MediaAsset] = {}
    for fixture, display_name, payload in _pilot_media_payloads():
        validated = validate_image_upload(
            payload,
            declared_mime="image/png",
            allowed_mime_types=frozenset({"image/png"}),
            max_bytes=5 * 1024 * 1024,
        )
        object_key = (
            f"organizations/{organization.id}/businesses/{business.id}/media/seed/{fixture}.png"
        )
        asset = session.scalar(
            select(MediaAsset).where(
                MediaAsset.organization_id == organization.id,
                MediaAsset.business_id == business.id,
                MediaAsset.object_key == object_key,
            )
        )
        if asset is not None:
            _require_owned_seed_asset(asset, fixture=fixture)
        # O storage não participa da transação SQL. Só escreva depois de provar
        # que uma chave existente pertence a este fixture determinístico.
        storage.put(object_key, validated.data, validated.mime_type)
        if asset is None:
            asset = MediaAsset(
                organization_id=organization.id,
                business_id=business.id,
                kind="IMAGE",
                storage_provider=storage.name,
                object_key=object_key,
                display_name=display_name,
                mime_type=validated.mime_type,
                byte_size=validated.byte_size,
                checksum_sha256=validated.checksum_sha256,
                width=validated.width,
                height=validated.height,
                origin="SEED",
                processing_status="READY",
                metadata_safe={"fixture": fixture, "fictional": True},
                created_by_user_id=admin.id,
            )
            session.add(asset)
            session.flush()
        else:
            asset.kind = "IMAGE"
            asset.storage_provider = storage.name
            asset.display_name = display_name
            asset.mime_type = validated.mime_type
            asset.byte_size = validated.byte_size
            asset.checksum_sha256 = validated.checksum_sha256
            asset.width = validated.width
            asset.height = validated.height
            asset.origin = "SEED"
            asset.processing_status = "READY"
            asset.metadata_safe = {"fixture": fixture, "fictional": True}
            asset.archived_at = None
        assets[fixture] = asset
    return assets


def _require_owned_seed_asset(asset: MediaAsset, *, fixture: str) -> None:
    if asset.metadata_safe.get("fixture") != fixture or asset.origin != "SEED":
        raise RuntimeError(
            f"A chave de mídia do piloto {fixture} já pertence a um arquivo não gerido "
            "por este seed; nenhum objeto foi sobrescrito"
        )


def _empty_brand_value(value: Any) -> bool:
    return (
        value is None
        or value == []
        or value == {}
        or (isinstance(value, str) and not value.strip())
    )


def _clone_default(value: Any) -> Any:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    return value


def _fill_pilot_brand_defaults(
    brand: BrandProfile,
    *,
    logo_asset_ids: list[UUID],
    visual_reference_asset_ids: list[UUID],
    increment_version: bool,
) -> bool:
    """Backfill only absent seed fields, preserving every customization."""

    defaults: dict[str, Any] = {
        "public_name": "Vet Demo",
        "description": (
            "Clínica veterinária inteiramente fictícia, criada para validar o fluxo "
            "operacional do GrowthOS em ambiente local."
        ),
        "segment": "Clínica veterinária",
        "audience": "Tutores fictícios de cães e gatos da região demonstrativa",
        "primary_colors": ["#1F7A6D", "#F4F1DE"],
        "secondary_colors": ["#FFFFFF", "#E9C46A"],
        "fonts": ["Inter", "Source Sans 3"],
        "logo_media_asset_ids": [str(asset_id) for asset_id in logo_asset_ids],
        "visual_reference_media_asset_ids": [
            str(asset_id) for asset_id in visual_reference_asset_ids
        ],
        "tone_of_voice": "acolhedor, claro e responsável",
        "preferred_words": ["cuidado responsável", "converse com a equipe", "prevenção"],
        "forbidden_words": ["cura garantida", "resultado imediato", "diagnóstico online"],
        "slogan": "Cuidado próximo em cada fase.",
        "differentiators": [
            "comunicação sem alarmismo",
            "revisão profissional de temas sensíveis",
            "orientação preventiva individualizada",
        ],
        "services": [
            "consulta preventiva",
            "planejamento vacinal individualizado",
            "acompanhamento de animais idosos",
        ],
        "contacts": {"email": "contato@vet-demo.example"},
        "links": ["https://vet-demo.example"],
        "calls_to_action": ["Agende uma conversa com nossa equipe."],
        "allowed_rules": [
            "explicar prevenção em linguagem simples",
            "indicar avaliação",
        ],
        "forbidden_rules": ["diagnosticar", "prescrever", "prometer resultado clínico"],
        "required_terms": ["conteúdo educativo", "avaliação veterinária"],
        "legal_rules": ["temas sensíveis exigem revisão profissional"],
        "image_restrictions": [
            "sem sangue",
            "sem procedimento invasivo",
            "sem medicamento",
        ],
        "internal_notes": "Todos os nomes, contatos, serviços e cenários são fictícios.",
    }
    changed = False
    for field, default in defaults.items():
        if _empty_brand_value(getattr(brand, field)):
            setattr(brand, field, _clone_default(default))
            changed = True
    if changed and increment_version:
        brand.version += 1
    return changed


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
    if content.current_version_id is None:
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
    first_version_id = session.scalar(
        select(ContentVersion.id).where(
            ContentVersion.organization_id == organization.id,
            ContentVersion.business_id == business.id,
            ContentVersion.content_item_id == content.id,
            ContentVersion.version_number == 1,
        )
    )
    if first_version_id is None:
        raise RuntimeError("Conteúdo demo publicado sem versão inicial")
    version_ids.add(first_version_id)
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
    asset = session.scalar(
        select(MediaAsset).where(
            MediaAsset.organization_id == organization.id,
            MediaAsset.business_id == business.id,
            MediaAsset.object_key == object_key,
        )
    )
    if asset is not None:
        _require_owned_seed_asset(asset, fixture="phase2-demo")
    storage.put(object_key, validated.data, validated.mime_type)
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
        elif association.media_asset_id != asset.id:
            raise RuntimeError(
                "A versão inicial publicada do demo já possui outra imagem principal; "
                "o seed preservou o vínculo existente"
            )
    return asset


def _ensure_pilot_content(
    session: Session,
    *,
    organization: Organization,
    business: Business,
    brand: BrandProfile,
    strategy: ContentStrategy,
    strategy_version: StrategyVersion,
    plan: ContentPlan,
    preset: VisualPreset,
    service: Service,
    audience: AudienceSegment,
    objective: MarketingObjective,
    admin: User,
    reviewer: User,
    media_asset: MediaAsset | None,
    revised_media_asset: MediaAsset | None = None,
    title: str,
    caption: str,
    suggested_for: datetime,
    sort_order: int,
    status: ContentStatus,
    approval_states: tuple[tuple[ApprovalComponent, ApprovalStatus, str | None], ...] = (),
    revised_caption: str | None = None,
    notes: str = "Conteúdo fictício para o roteiro de piloto local.",
) -> tuple[CalendarEntry, ContentItem]:
    """Create a deterministic, tenant-scoped pilot fixture without paid providers."""
    entry = session.scalar(
        select(CalendarEntry).where(
            CalendarEntry.organization_id == organization.id,
            CalendarEntry.business_id == business.id,
            CalendarEntry.content_plan_id == plan.id,
            CalendarEntry.title == title,
            CalendarEntry.suggested_for == suggested_for,
        )
    )
    if entry is None:
        entry = CalendarEntry(
            organization_id=organization.id,
            business_id=business.id,
            content_plan_id=plan.id,
            visual_preset_id=preset.id,
            title=title,
            objective=objective.description,
            audience=audience.name,
            channel="Instagram",
            format=preset.format,
            suggested_for=suggested_for,
            status="GENERATED",
            notes="Pauta fictícia do roteiro de piloto da versão 1.0.",
            sort_order=sort_order,
            created_by_user_id=admin.id,
        )
        session.add(entry)
        session.flush()

    content = session.scalar(
        select(ContentItem).where(
            ContentItem.organization_id == organization.id,
            ContentItem.business_id == business.id,
            ContentItem.calendar_entry_id == entry.id,
        )
    )
    if content is None:
        if entry.content_item_id is not None:
            raise RuntimeError(
                f"A pauta demo '{title}' aponta para outro conteúdo; "
                "preserve os dados e corrija o vínculo antes de executar o seed"
            )
        content = ContentItem(
            organization_id=organization.id,
            business_id=business.id,
            status=status,
            content_strategy_id=strategy.id,
            strategy_version_id=strategy_version.id,
            content_plan_id=plan.id,
            calendar_entry_id=entry.id,
            visual_preset_id=preset.id,
            scheduled_for=suggested_for,
            created_by_user_id=admin.id,
        )
        session.add(content)
        session.flush()
        entry.content_item_id = content.id
    elif entry.content_item_id is None:
        entry.content_item_id = content.id
    elif entry.content_item_id != content.id:
        raise RuntimeError(
            f"A pauta demo '{title}' possui vínculos de conteúdo conflitantes; "
            "o seed não substituirá dados existentes"
        )

    current_version = None
    if content.current_version_id is not None:
        current_version = session.scalar(
            select(ContentVersion).where(
                ContentVersion.id == content.current_version_id,
                ContentVersion.organization_id == organization.id,
                ContentVersion.business_id == business.id,
                ContentVersion.content_item_id == content.id,
            )
        )
        if current_version is None:
            raise RuntimeError(
                f"O conteúdo demo '{title}' aponta para uma versão conflitante; "
                "o seed não sequestrará o vínculo"
            )

    first_version = session.scalar(
        select(ContentVersion).where(
            ContentVersion.organization_id == organization.id,
            ContentVersion.business_id == business.id,
            ContentVersion.content_item_id == content.id,
            ContentVersion.version_number == 1,
        )
    )
    if first_version is None:
        if current_version is not None:
            raise RuntimeError(
                f"O conteúdo demo '{title}' perdeu sua versão inicial; "
                "preserve o histórico e repare-o antes de executar o seed"
            )
        first_version = ContentVersion(
            organization_id=organization.id,
            business_id=business.id,
            content_item_id=content.id,
            version_number=1,
            title=title,
            caption=caption,
            channel="Instagram",
            format=preset.format,
            objective=objective.description,
            audience=audience.name,
            cta=preset.default_cta,
            service_id=service.id,
            audience_segment_id=audience.id,
            marketing_objective_id=objective.id,
            notes=notes,
            script="Roteiro determinístico gerado pelo provider mock para o piloto local.",
            visual_prompt=(
                f"[mock] {preset.base_prompt}; {preset.composition}; "
                f"proporção {preset.aspect_ratio}."
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
        _assess_seed_content_version(first_version)
        session.add(first_version)
        session.flush()
        content.current_version_id = first_version.id
        current_version = first_version
    elif current_version is None:
        content.current_version_id = first_version.id
        current_version = first_version

    decision_time = datetime.now(UTC)
    for component, approval_status, comment in approval_states:
        approval = session.scalar(
            select(Approval).where(
                Approval.organization_id == organization.id,
                Approval.business_id == business.id,
                Approval.content_item_id == content.id,
                Approval.content_version_id == first_version.id,
                Approval.stage == ApprovalStage.CLIENT,
                Approval.component == component,
            )
        )
        if approval is None:
            decided = approval_status != ApprovalStatus.PENDING
            session.add(
                Approval(
                    organization_id=organization.id,
                    business_id=business.id,
                    content_item_id=content.id,
                    content_version_id=first_version.id,
                    stage=ApprovalStage.CLIENT,
                    component=component,
                    status=approval_status,
                    requested_by_user_id=admin.id,
                    decided_by_user_id=reviewer.id if decided else None,
                    decision_comment=comment,
                    decided_at=decision_time if decided else None,
                )
            )

    version_media: list[tuple[ContentVersion, MediaAsset | None]] = [(first_version, media_asset)]
    assert current_version is not None
    if revised_caption is not None:
        revised_version = session.scalar(
            select(ContentVersion).where(
                ContentVersion.organization_id == organization.id,
                ContentVersion.business_id == business.id,
                ContentVersion.content_item_id == content.id,
                ContentVersion.version_number == 2,
            )
        )
        if revised_version is None:
            revised_version = ContentVersion(
                organization_id=organization.id,
                business_id=business.id,
                content_item_id=content.id,
                version_number=2,
                title=title,
                caption=revised_caption,
                channel=first_version.channel,
                format=first_version.format,
                objective=first_version.objective,
                audience=first_version.audience,
                cta=first_version.cta,
                service_id=first_version.service_id,
                audience_segment_id=first_version.audience_segment_id,
                marketing_objective_id=first_version.marketing_objective_id,
                notes="Revisão fictícia criada após um pedido de alteração no texto.",
                script=first_version.script,
                visual_prompt=first_version.visual_prompt,
                negative_prompt=first_version.negative_prompt,
                brand_context_snapshot=dict(first_version.brand_context_snapshot),
                visual_preset_snapshot=dict(first_version.visual_preset_snapshot),
                provider_name="manual_revision",
                created_by_user_id=admin.id,
            )
            _assess_seed_content_version(revised_version)
            session.add(revised_version)
            session.flush()
        elif (
            revised_version.provider_name != "manual_revision"
            or revised_version.caption != revised_caption
        ):
            raise RuntimeError(
                f"O conteúdo demo '{title}' já possui uma versão 2 que não é do seed; "
                "o histórico foi preservado. Use make reset somente se puder apagar o demo local."
            )
        if current_version.version_number <= first_version.version_number:
            content.current_version_id = revised_version.id
            current_version = revised_version
        version_media.append((revised_version, revised_media_asset or media_asset))

    for version, version_asset in version_media:
        if version_asset is not None:
            association = session.scalar(
                select(ContentVersionMedia).where(
                    ContentVersionMedia.organization_id == organization.id,
                    ContentVersionMedia.business_id == business.id,
                    ContentVersionMedia.content_version_id == version.id,
                    ContentVersionMedia.role == "PRIMARY",
                )
            )
            if association is None:
                session.add(
                    ContentVersionMedia(
                        organization_id=organization.id,
                        business_id=business.id,
                        content_version_id=version.id,
                        media_asset_id=version_asset.id,
                        role="PRIMARY",
                        sort_order=0,
                        created_by_user_id=admin.id,
                    )
                )
            elif association.media_asset_id != version_asset.id:
                raise RuntimeError(
                    f"A versão {version.version_number} do conteúdo demo '{title}' "
                    "já possui outra imagem principal; o seed preservou o vínculo existente"
                )

    return entry, content


def _ensure_pilot_notification(
    session: Session,
    *,
    organization: Organization,
    business: Business,
    recipient: User,
    notification_type: str,
    category: NotificationCategory,
    importance: NotificationImportance,
    title: str,
    message: str,
    resource: ContentItem,
    created_at: datetime | None = None,
) -> Notification:
    notification = session.scalar(
        select(Notification).where(
            Notification.organization_id == organization.id,
            Notification.business_id == business.id,
            Notification.recipient_user_id == recipient.id,
            Notification.type == notification_type,
            Notification.resource_type == "content_item",
            Notification.resource_id == resource.id,
        )
    )
    if notification is None:
        notification = Notification(
            organization_id=organization.id,
            business_id=business.id,
            recipient_user_id=recipient.id,
            type=notification_type,
            category=category,
            importance=importance,
            title=title,
            message=message,
            resource_type="content_item",
            resource_id=resource.id,
            **({"created_at": created_at} if created_at is not None else {}),
        )
        session.add(notification)
    else:
        # Classificação é um invariante do fixture; leitura e texto do usuário
        # permanecem intactos em toda reexecução.
        notification.category = category
        notification.importance = importance
    return notification


def _ensure_completed_pilot_onboarding(
    session: Session,
    *,
    organization: Organization,
    business: Business,
    brand: BrandProfile,
    services: list[Service],
    audiences: list[AudienceSegment],
    objectives: list[MarketingObjective],
    preset: VisualPreset,
    admin: User,
    reviewer: User,
) -> BusinessOnboarding:
    onboarding = session.scalar(
        select(BusinessOnboarding).where(
            BusinessOnboarding.organization_id == organization.id,
            BusinessOnboarding.business_id == business.id,
        )
    )
    if onboarding is not None:
        expected_status = "COMPLETED" if onboarding.status == "COMPLETED" else "IN_PROGRESS"
        business.onboarding_status = expected_status
        if onboarding.status == "COMPLETED" and business.onboarding_completed_at is None:
            business.onboarding_completed_at = onboarding.completed_at
        return onboarding

    if business.onboarding_status == "IN_PROGRESS":
        raise RuntimeError(
            "A clínica demo indica onboarding em andamento, mas o registro não existe. "
            "Preserve os dados e corrija o vínculo antes de executar o seed novamente."
        )
    reviewer_membership = session.scalar(
        select(Membership).where(
            Membership.organization_id == organization.id,
            Membership.business_id == business.id,
            Membership.user_id == reviewer.id,
            Membership.role.in_([Role.CLIENT_OWNER, Role.CLIENT_REVIEWER]),
            Membership.is_active.is_(True),
        )
    )
    if reviewer_membership is None:
        raise RuntimeError("A clínica demo precisa de um revisor ativo para concluir o onboarding")
    if not brand.logo_media_asset_ids or not brand.visual_reference_media_asset_ids:
        raise RuntimeError("O Brand Kit demo precisa de logo e referência visual para o onboarding")

    completed_at = business.onboarding_completed_at or datetime.now(UTC)
    step_data: dict[str, dict[str, Any]] = {
        "1": {
            "name": business.name,
            "brand_name": brand.brand_name,
            "public_name": brand.public_name,
            "description": brand.description,
            "timezone": business.timezone,
        },
        "2": {"segment": business.segment},
        "3": {
            "services": [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "description": item.description,
                    "category": item.category,
                    "warnings": list(item.warnings),
                }
                for item in services
            ]
        },
        "4": {
            "audiences": [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "description": item.description,
                    "needs": list(item.needs),
                    "objections": list(item.objections),
                    "location": item.location,
                }
                for item in audiences
            ]
        },
        "5": {
            "objectives": [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "description": item.description,
                    "planned_indicators": list(item.planned_indicators),
                }
                for item in objectives
            ]
        },
        "6": {"differentiators": list(brand.differentiators)},
        "7": {
            "tone_of_voice": brand.tone_of_voice,
            "preferred_words": list(brand.preferred_words),
            "forbidden_words": list(brand.forbidden_words),
        },
        "8": {"logo_media_asset_ids": list(brand.logo_media_asset_ids)},
        "9": {
            "primary_colors": list(brand.primary_colors),
            "secondary_colors": list(brand.secondary_colors),
            "fonts": list(brand.fonts),
        },
        "10": {"visual_reference_media_asset_ids": list(brand.visual_reference_media_asset_ids)},
        "11": {
            "allowed_rules": list(brand.allowed_rules),
            "forbidden_rules": list(brand.forbidden_rules),
            "required_terms": list(brand.required_terms),
            "legal_rules": list(brand.legal_rules),
            "image_restrictions": list(brand.image_restrictions),
        },
        "12": {"membership_ids": [str(reviewer_membership.id)]},
        "13": {
            "email_enabled": True,
            "mode": "IMMEDIATE",
            "timezone": business.timezone,
            "digest_time": "09:00:00",
            "weekly_day": 1,
            "disabled_categories": [],
        },
        "14": {"preset_id": str(preset.id)},
        "15": {
            "confirmed": True,
            "notes": "Cadastro fictício revisado para o piloto local da versão 1.0.",
        },
    }
    onboarding = BusinessOnboarding(
        organization_id=organization.id,
        business_id=business.id,
        status="COMPLETED",
        current_step=15,
        completed_steps=list(range(1, 16)),
        step_data=step_data,
        revision=1,
        started_by_user_id=admin.id,
        updated_by_user_id=admin.id,
        completed_by_user_id=admin.id,
        completed_at=completed_at,
    )
    session.add(onboarding)
    business.onboarding_status = "COMPLETED"
    business.onboarding_completed_at = completed_at
    return onboarding


def _ensure_pilot_notification_preference(
    session: Session,
    *,
    organization: Organization,
    business: Business,
    admin: User,
) -> None:
    existing = session.scalar(
        select(NotificationPreference.id).where(
            NotificationPreference.organization_id == organization.id,
            NotificationPreference.user_id == admin.id,
        )
    )
    if existing is not None:
        return
    upsert_notification_preference(
        session,
        organization_id=organization.id,
        user_id=admin.id,
        actor_user_id=admin.id,
        business_id=business.id,
        payload=NotificationPreferenceUpdate(
            email_enabled=True,
            timezone=business.timezone,
            digest_time=time(hour=9),
            weekly_day=1,
            categories=[
                NotificationCategoryPreferenceInput(
                    category=category,
                    delivery_mode=NotificationDeliveryMode.IMMEDIATE,
                    is_enabled=True,
                )
                for category in NotificationCategory
            ],
        ),
    )


def _grant_initial_pilot_professional_review(
    session: Session,
    *,
    organization: Organization,
    business: Business,
    admin: User,
    reviewer: User,
) -> None:
    membership = session.scalar(
        select(Membership).where(
            Membership.organization_id == organization.id,
            Membership.business_id == business.id,
            Membership.user_id == reviewer.id,
            Membership.role.in_([Role.CLIENT_OWNER, Role.CLIENT_REVIEWER]),
            Membership.is_active.is_(True),
        )
    )
    if membership is None:
        raise RuntimeError("A clínica demo precisa de um revisor profissional ativo")
    if membership.professional_review_granted:
        return
    membership.professional_review_granted = True
    reviewer.session_version += 1
    add_audit_log(
        session,
        organization_id=organization.id,
        business_id=business.id,
        actor_user_id=admin.id,
        action="membership.professional_review_grant_changed",
        resource_type="membership",
        resource_id=membership.id,
        details={
            "granted": True,
            "role": membership.role.value,
            "source": "demo_seed",
        },
    )


def _seed_phase2_demo(
    session: Session,
    *,
    organization: Organization,
    business: Business,
    brand: BrandProfile,
    brand_was_created: bool,
    admin: User,
    reviewer: User,
    storage: StorageProvider,
) -> dict[str, UUID]:
    pilot_was_initialized = (
        session.scalar(
            select(StrategyVersion.id).where(
                StrategyVersion.organization_id == organization.id,
                StrategyVersion.business_id == business.id,
                StrategyVersion.provider_reference == _PILOT_STRATEGY_REFERENCE,
            )
        )
        is not None
    )
    if not pilot_was_initialized:
        _grant_initial_pilot_professional_review(
            session,
            organization=organization,
            business=business,
            admin=admin,
            reviewer=reviewer,
        )
    pilot_media = _ensure_pilot_media_assets(
        session,
        organization=organization,
        business=business,
        admin=admin,
        storage=storage,
    )
    square_before_asset = pilot_media["phase3-pilot-square-before"]
    square_after_asset = pilot_media["phase3-pilot-square-after"]
    vertical_asset = pilot_media["phase3-pilot-vertical"]
    if brand_was_created or not pilot_was_initialized:
        _fill_pilot_brand_defaults(
            brand,
            logo_asset_ids=[square_after_asset.id],
            visual_reference_asset_ids=[square_before_asset.id, vertical_asset.id],
            increment_version=not brand_was_created,
        )

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

    services = [service]
    for service_name, description, category, warnings in (
        (
            "Planejamento vacinal individualizado",
            "Organização fictícia do calendário preventivo com avaliação profissional.",
            "Prevenção",
            ["O plano depende da espécie, idade e histórico avaliados pela equipe veterinária."],
        ),
        (
            "Acompanhamento de animais idosos",
            "Rotina fictícia de acompanhamento para cães e gatos em fase sênior.",
            "Longevidade",
            ["Não oferece diagnóstico; sinais clínicos exigem atendimento profissional."],
        ),
    ):
        extra_service = session.scalar(
            select(Service).where(
                Service.organization_id == organization.id,
                Service.business_id == business.id,
                Service.name == service_name,
            )
        )
        if extra_service is None:
            extra_service = Service(
                organization_id=organization.id,
                business_id=business.id,
                name=service_name,
                description=description,
                category=category,
                warnings=warnings,
            )
            session.add(extra_service)
            session.flush()
        services.append(extra_service)

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

    audiences = [audience]
    for audience_name, description, needs, objections in (
        (
            "Tutores de animais idosos",
            "Famílias fictícias que buscam uma rotina responsável para pets em fase sênior.",
            ["orientação preventiva", "acompanhamento compreensível"],
            ["medo de procedimentos desnecessários"],
        ),
        (
            "Famílias com rotina preventiva",
            "Pessoas fictícias que desejam organizar cuidados recorrentes sem alarmismo.",
            ["planejamento", "comunicação objetiva"],
            ["dificuldade de manter o calendário em dia"],
        ),
    ):
        extra_audience = session.scalar(
            select(AudienceSegment).where(
                AudienceSegment.organization_id == organization.id,
                AudienceSegment.business_id == business.id,
                AudienceSegment.name == audience_name,
            )
        )
        if extra_audience is None:
            extra_audience = AudienceSegment(
                organization_id=organization.id,
                business_id=business.id,
                name=audience_name,
                description=description,
                needs=needs,
                objections=objections,
                location="Região fictícia da clínica demo",
            )
            session.add(extra_audience)
            session.flush()
        audiences.append(extra_audience)

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

    objectives = [objective]
    for objective_name, description, indicators in (
        (
            "Estimular conversas de agendamento",
            "Convidar o tutor a conversar com a equipe sem prometer resultado clínico.",
            ["conteúdos aprovados", "publicações registradas manualmente"],
        ),
        (
            "Fortalecer confiança na equipe",
            "Apresentar o cuidado responsável e a revisão profissional da clínica fictícia.",
            ["revisões concluídas", "conteúdos sem pendência"],
        ),
    ):
        extra_objective = session.scalar(
            select(MarketingObjective).where(
                MarketingObjective.organization_id == organization.id,
                MarketingObjective.business_id == business.id,
                MarketingObjective.name == objective_name,
            )
        )
        if extra_objective is None:
            extra_objective = MarketingObjective(
                organization_id=organization.id,
                business_id=business.id,
                name=objective_name,
                description=description,
                planned_indicators=indicators,
            )
            session.add(extra_objective)
            session.flush()
        objectives.append(extra_objective)

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

    vertical_preset = session.scalar(
        select(VisualPreset).where(
            VisualPreset.organization_id == organization.id,
            VisualPreset.business_id == business.id,
            VisualPreset.name == "Stories: pergunta responsável",
        )
    )
    if vertical_preset is None:
        vertical_preset = VisualPreset(
            organization_id=organization.id,
            business_id=business.id,
            brand_profile_id=brand.id,
            name="Stories: pergunta responsável",
            objective="Abrir uma conversa educativa sem diagnosticar ou prescrever.",
            format="Stories",
            aspect_ratio="9:16",
            creation_mode="TEMPLATE",
            color_palette=["#1F7A6D", "#F4F1DE", "#FFFFFF", "#E9C46A"],
            fonts=["Inter", "Source Sans 3"],
            logo_position="superior esquerdo",
            logo_scale_percent=12,
            safe_margins={"top": 10, "right": 8, "bottom": 14, "left": 8},
            background_style="fundo claro com formas orgânicas e área central livre",
            photographic_style="registro cotidiano acolhedor, sem procedimento clínico",
            realism_level="natural",
            lighting="luz natural difusa",
            composition="pergunta curta no topo e animal saudável em ambiente doméstico",
            max_text_characters=70,
            text_rules=["uma pergunta por tela", "alto contraste", "sem diagnóstico"],
            base_prompt="Cena vertical educativa sobre rotina veterinária responsável.",
            negative_prompt="sem diagnóstico, sem medicamento, sem sangue, sem texto ilegível",
            allowed_elements=["animal saudável", "tutor", "ambiente doméstico seguro"],
            forbidden_elements=["procedimento invasivo", "medicação", "promessa de cura"],
            visual_signature="verde profundo, creme e destaque amarelo pontual",
            default_cta="Converse com nossa equipe veterinária.",
            created_by_user_id=admin.id,
            updated_by_user_id=admin.id,
        )
        session.add(vertical_preset)
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
            service_snapshots=[{"id": str(item.id), "name": item.name} for item in services],
            audience_snapshots=[{"id": str(item.id), "name": item.name} for item in audiences],
            objective_snapshots=[{"id": str(item.id), "name": item.name} for item in objectives],
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

    first_strategy_version = session.scalar(
        select(StrategyVersion).where(
            StrategyVersion.organization_id == organization.id,
            StrategyVersion.business_id == business.id,
            StrategyVersion.content_strategy_id == strategy.id,
            StrategyVersion.version_number == 1,
        )
    )
    if first_strategy_version is None:
        raise RuntimeError("Estratégia demo existente sem versão inicial válida")
    if (
        first_strategy_version.source != "MOCK"
        or first_strategy_version.provider_name != "mock"
        or first_strategy_version.provider_reference != "seed-phase2-v1"
    ):
        raise RuntimeError(
            "A versão inicial da estratégia demo não foi criada pelo seed legado; "
            "nenhuma nova versão será anexada a dados do usuário"
        )
    pilot_strategy_version = session.scalar(
        select(StrategyVersion).where(
            StrategyVersion.organization_id == organization.id,
            StrategyVersion.business_id == business.id,
            StrategyVersion.content_strategy_id == strategy.id,
            StrategyVersion.version_number == 2,
        )
    )
    if pilot_strategy_version is None:
        pilot_strategy_version = StrategyVersion(
            organization_id=organization.id,
            business_id=business.id,
            content_strategy_id=strategy.id,
            version_number=2,
            objective=(
                "Organizar um mês de educação preventiva, acolhimento e longevidade "
                "com revisão responsável."
            ),
            positioning=(
                "A clínica próxima que explica limites, evita promessas e encaminha "
                "temas sensíveis para revisão profissional."
            ),
            funnel=["descoberta", "educação", "conversa"],
            channels=["Instagram"],
            pillars=[
                {"name": "Prevenção", "description": "Hábitos e consultas de rotina"},
                {"name": "Acolhimento", "description": "Relação entre tutor, animal e equipe"},
                {"name": "Longevidade", "description": "Rotina responsável para pets idosos"},
            ],
            planned_indicators=[
                "conteúdos aprovados",
                "pedidos de alteração tratados",
                "publicações registradas manualmente",
            ],
            service_snapshots=[{"id": str(item.id), "name": item.name} for item in services],
            audience_snapshots=[{"id": str(item.id), "name": item.name} for item in audiences],
            objective_snapshots=[{"id": str(item.id), "name": item.name} for item in objectives],
            brand_context_snapshot={
                "brand_name": brand.brand_name,
                "tone_of_voice": brand.tone_of_voice,
                "primary_colors": list(brand.primary_colors),
            },
            source="MOCK",
            provider_name="mock",
            provider_reference=_PILOT_STRATEGY_REFERENCE,
            created_by_user_id=admin.id,
            supersedes_version_id=first_strategy_version.id,
        )
        session.add(pilot_strategy_version)
        session.flush()
    elif (
        pilot_strategy_version.provider_reference != _PILOT_STRATEGY_REFERENCE
        or pilot_strategy_version.provider_name != "mock"
        or pilot_strategy_version.source != "MOCK"
        or pilot_strategy_version.supersedes_version_id != first_strategy_version.id
    ):
        raise RuntimeError(
            "A estratégia demo já possui uma versão 2 que não foi criada pelo "
            "seed da Fase 3. O histórico foi preservado; use make reset somente se "
            "puder apagar os dados locais de demonstração."
        )
    upgrading_legacy_strategy = strategy.current_version_id == first_strategy_version.id
    if upgrading_legacy_strategy:
        strategy.current_version_id = pilot_strategy_version.id
        if strategy.approved_version_id == first_strategy_version.id:
            strategy.approved_version_id = pilot_strategy_version.id
    seed_strategy_version = pilot_strategy_version

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
            strategy_version_id=seed_strategy_version.id,
            name="Calendário editorial demo",
            starts_on=starts_on,
            ends_on=ends_on,
            frequency="SEMANAL",
            status="ACTIVE",
            created_by_user_id=admin.id,
        )
        session.add(plan)
        session.flush()
    elif (
        plan.strategy_version_id == first_strategy_version.id
        and strategy.current_version_id == pilot_strategy_version.id
    ):
        plan.strategy_version_id = pilot_strategy_version.id

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
        if calendar_entry.content_item_id is not None:
            raise RuntimeError(
                "A pauta publicada demo aponta para outro conteúdo; o seed preservou o conflito"
            )
        content = ContentItem(
            organization_id=organization.id,
            business_id=business.id,
            status=ContentStatus.PUBLISHED,
            content_strategy_id=strategy.id,
            strategy_version_id=seed_strategy_version.id,
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
        _assess_seed_content_version(content_version)
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
    elif calendar_entry.content_item_id is None:
        calendar_entry.content_item_id = content.id
    elif calendar_entry.content_item_id != content.id:
        raise RuntimeError(
            "A pauta publicada demo possui vínculos conflitantes; o seed não os substituirá"
        )

    current_content_version = None
    if content.current_version_id is not None:
        current_content_version = session.scalar(
            select(ContentVersion).where(
                ContentVersion.id == content.current_version_id,
                ContentVersion.organization_id == organization.id,
                ContentVersion.business_id == business.id,
                ContentVersion.content_item_id == content.id,
            )
        )
        if current_content_version is None:
            raise RuntimeError(
                "O conteúdo publicado demo aponta para uma versão conflitante; "
                "o seed preservou o vínculo"
            )
    first_content_version = session.scalar(
        select(ContentVersion).where(
            ContentVersion.organization_id == organization.id,
            ContentVersion.business_id == business.id,
            ContentVersion.content_item_id == content.id,
            ContentVersion.version_number == 1,
        )
    )
    if first_content_version is None:
        raise RuntimeError("O conteúdo publicado demo perdeu sua versão inicial")
    if current_content_version is None:
        content.current_version_id = first_content_version.id

    _ensure_pilot_notification(
        session,
        organization=organization,
        business=business,
        recipient=admin,
        notification_type="CONTENT_DECISION",
        category=NotificationCategory.CONTENT_APPROVED,
        importance=NotificationImportance.NORMAL,
        title="Conteúdo demo aprovado",
        message="Texto e imagem do conteúdo fictício foram aprovados.",
        resource=content,
        created_at=suggested_for,
    )

    media_asset = _ensure_phase2_demo_media(
        session,
        organization=organization,
        business=business,
        content=content,
        admin=admin,
        storage=storage,
    )

    def pilot_date(day: int, hour: int = 14) -> datetime:
        return datetime(
            starts_on.year,
            starts_on.month,
            min(day, ends_on.day),
            hour,
            tzinfo=UTC,
        )

    _, changes_content = _ensure_pilot_content(
        session,
        organization=organization,
        business=business,
        brand=brand,
        strategy=strategy,
        strategy_version=seed_strategy_version,
        plan=plan,
        preset=vertical_preset,
        service=services[1],
        audience=audiences[2],
        objective=objectives[1],
        admin=admin,
        reviewer=reviewer,
        media_asset=vertical_asset,
        title="Como preparar o pet para a consulta",
        caption=(
            "Organizar documentos e anotar dúvidas ajuda a aproveitar a conversa com a "
            "equipe veterinária. Cada animal precisa de avaliação individual."
        ),
        suggested_for=pilot_date(8),
        sort_order=1,
        status=ContentStatus.CHANGES_REQUESTED,
        approval_states=(
            (
                ApprovalComponent.IMAGE,
                ApprovalStatus.APPROVED,
                "Visual fictício aprovado antes da revisão do texto.",
            ),
            (
                ApprovalComponent.TEXT,
                ApprovalStatus.CHANGES_REQUESTED,
                "Explique melhor o que deve ser levado, sem transformar em orientação clínica.",
            ),
        ),
    )

    _, revised_content = _ensure_pilot_content(
        session,
        organization=organization,
        business=business,
        brand=brand,
        strategy=strategy,
        strategy_version=seed_strategy_version,
        plan=plan,
        preset=preset,
        service=service,
        audience=audience,
        objective=objective,
        admin=admin,
        reviewer=reviewer,
        media_asset=square_before_asset,
        revised_media_asset=square_after_asset,
        title="Enriquecimento ambiental em casa",
        caption=(
            "Brincadeiras deixam qualquer pet saudável e resolvem o estresse. "
            "Veja três ideias para hoje."
        ),
        revised_caption=(
            "Atividades adequadas à espécie e à rotina podem favorecer o bem-estar. "
            "Converse com a equipe veterinária quando houver mudança de comportamento."
        ),
        suggested_for=pilot_date(12),
        sort_order=2,
        status=ContentStatus.DRAFT,
        approval_states=(
            (
                ApprovalComponent.IMAGE,
                ApprovalStatus.APPROVED,
                "Composição fictícia aprovada.",
            ),
            (
                ApprovalComponent.TEXT,
                ApprovalStatus.CHANGES_REQUESTED,
                "Remova a generalização e inclua o limite da orientação educativa.",
            ),
        ),
    )

    _, review_content = _ensure_pilot_content(
        session,
        organization=organization,
        business=business,
        brand=brand,
        strategy=strategy,
        strategy_version=seed_strategy_version,
        plan=plan,
        preset=vertical_preset,
        service=services[2],
        audience=audiences[1],
        objective=objectives[2],
        admin=admin,
        reviewer=reviewer,
        media_asset=vertical_asset,
        title="Rotina responsável para pets idosos",
        caption=(
            "Mudanças de rotina merecem observação cuidadosa. A equipe veterinária pode "
            "orientar um acompanhamento adequado para cada fase da vida."
        ),
        suggested_for=pilot_date(19),
        sort_order=3,
        status=ContentStatus.CLIENT_REVIEW,
        approval_states=(
            (ApprovalComponent.TEXT, ApprovalStatus.PENDING, None),
            (ApprovalComponent.IMAGE, ApprovalStatus.PENDING, None),
        ),
    )

    _, sensitive_content = _ensure_pilot_content(
        session,
        organization=organization,
        business=business,
        brand=brand,
        strategy=strategy,
        strategy_version=seed_strategy_version,
        plan=plan,
        preset=preset,
        service=services[2],
        audience=audiences[1],
        objective=objectives[0],
        admin=admin,
        reviewer=reviewer,
        media_asset=None,
        title="Sinais de alerta: quando buscar avaliação",
        caption=(
            f"{_PILOT_SENSITIVE_MARKER} Se o pet apresentar perda de apetite e falta de ar, "
            "procure um veterinário imediatamente para avaliação individual. "
            "Este rascunho não diagnostica, não prescreve e não deve ser publicado."
        ),
        suggested_for=pilot_date(23),
        sort_order=4,
        status=ContentStatus.CLIENT_REVIEW,
        approval_states=(
            (ApprovalComponent.TEXT, ApprovalStatus.PENDING, None),
            (ApprovalComponent.IMAGE, ApprovalStatus.PENDING, None),
        ),
        notes=(
            f"{_PILOT_SENSITIVE_MARKER} Fixture sem dado clínico ou pessoal real; "
            "mantenha bloqueada até a revisão profissional."
        ),
    )

    for recipient, notification_type, category, importance, title, message, resource in (
        (
            admin,
            "CONTENT_DECISION",
            NotificationCategory.CONTENT_CHANGES_REQUESTED,
            NotificationImportance.NORMAL,
            "Alteração solicitada no piloto",
            "O cliente fictício pediu uma alteração no texto do conteúdo de preparação.",
            changes_content,
        ),
        (
            reviewer,
            "CONTENT_REVIEW_REQUESTED",
            NotificationCategory.CONTENT_AWAITING_APPROVAL,
            NotificationImportance.URGENT,
            "Conteúdo piloto para revisar",
            "Texto e imagem do conteúdo fictício sobre pets idosos aguardam decisão.",
            review_content,
        ),
    ):
        _ensure_pilot_notification(
            session,
            organization=organization,
            business=business,
            recipient=recipient,
            notification_type=notification_type,
            category=category,
            importance=importance,
            title=title,
            message=message,
            resource=resource,
        )

    onboarding = _ensure_completed_pilot_onboarding(
        session,
        organization=organization,
        business=business,
        brand=brand,
        services=services,
        audiences=audiences,
        objectives=objectives,
        preset=preset,
        admin=admin,
        reviewer=reviewer,
    )
    _ensure_pilot_notification_preference(
        session,
        organization=organization,
        business=business,
        admin=admin,
    )
    session.flush()

    return {
        "service_id": service.id,
        "audience_id": audience.id,
        "objective_id": objective.id,
        "visual_preset_id": preset.id,
        "strategy_id": strategy.id,
        "strategy_version_id": seed_strategy_version.id,
        "content_plan_id": plan.id,
        "calendar_entry_id": calendar_entry.id,
        "content_id": content.id,
        "media_asset_id": media_asset.id,
        "pilot_square_before_media_asset_id": square_before_asset.id,
        "pilot_square_after_media_asset_id": square_after_asset.id,
        "pilot_vertical_media_asset_id": vertical_asset.id,
        "onboarding_id": onboarding.id,
        "changes_requested_content_id": changes_content.id,
        "revised_content_id": revised_content.id,
        "review_content_id": review_content.id,
        "sensitive_content_id": sensitive_content.id,
        "secondary_visual_preset_id": vertical_preset.id,
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
    session.flush()

    brand = session.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == organization.id,
            BrandProfile.business_id == business.id,
        )
    )
    brand_was_created = brand is None
    if brand is None:
        brand = BrandProfile(
            organization_id=organization.id,
            business_id=business.id,
            brand_name="Clínica Veterinária Demo",
            public_name="Vet Demo",
            description=(
                "Clínica veterinária inteiramente fictícia, criada para validar o fluxo "
                "operacional do GrowthOS em ambiente local."
            ),
            segment="Clínica veterinária",
            audience="Tutores fictícios de cães e gatos da região demonstrativa",
            primary_colors=["#1F7A6D", "#F4F1DE"],
            secondary_colors=["#FFFFFF", "#E9C46A"],
            fonts=["Inter", "Source Sans 3"],
            tone_of_voice="acolhedor, claro e responsável",
            preferred_words=["cuidado responsável", "converse com a equipe", "prevenção"],
            forbidden_words=["cura garantida", "resultado imediato", "diagnóstico online"],
            slogan="Cuidado próximo em cada fase.",
            differentiators=[
                "comunicação sem alarmismo",
                "revisão profissional de temas sensíveis",
                "orientação preventiva individualizada",
            ],
            services=[
                "consulta preventiva",
                "planejamento vacinal individualizado",
                "acompanhamento de animais idosos",
            ],
            contacts={"email": "contato@vet-demo.example"},
            links=["https://vet-demo.example"],
            calls_to_action=["Agende uma conversa com nossa equipe."],
            allowed_rules=["explicar prevenção em linguagem simples", "indicar avaliação"],
            forbidden_rules=["diagnosticar", "prescrever", "prometer resultado clínico"],
            required_terms=["conteúdo educativo", "avaliação veterinária"],
            legal_rules=["temas sensíveis exigem revisão profissional"],
            image_restrictions=["sem sangue", "sem procedimento invasivo", "sem medicamento"],
            internal_notes="Todos os nomes, contatos, serviços e cenários são fictícios.",
        )
        session.add(brand)
        session.flush()
    phase2 = _seed_phase2_demo(
        session,
        organization=organization,
        business=business,
        brand=brand,
        brand_was_created=brand_was_created,
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
