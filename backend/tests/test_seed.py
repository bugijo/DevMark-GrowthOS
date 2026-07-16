import io
from hashlib import sha256

from PIL import Image
from sqlalchemy import func, select

from growthos.database import get_session_factory
from growthos.domain.enums import ApprovalComponent
from growthos.models import (
    Approval,
    AudienceSegment,
    CalendarEntry,
    ContentItem,
    ContentPlan,
    ContentStrategy,
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
from growthos.seed import seed_demo
from growthos.services.storage import MemoryStorageProvider


def test_seed_is_idempotent_and_uses_distinct_client_credentials() -> None:
    storage = MemoryStorageProvider()
    with get_session_factory()() as session:
        first = seed_demo(session, storage=storage)
        second = seed_demo(session, storage=storage)
        assert first == second
        assert session.scalar(select(func.count()).select_from(Organization)) == 1
        assert session.scalar(select(func.count()).select_from(User)) == 2
        assert session.scalar(select(func.count()).select_from(Membership)) == 2
        assert session.scalar(select(func.count()).select_from(Service)) == 1
        assert session.scalar(select(func.count()).select_from(AudienceSegment)) == 1
        assert session.scalar(select(func.count()).select_from(MarketingObjective)) == 1
        assert session.scalar(select(func.count()).select_from(VisualPreset)) == 1
        assert session.scalar(select(func.count()).select_from(ContentStrategy)) == 1
        assert session.scalar(select(func.count()).select_from(StrategyVersion)) == 1
        assert session.scalar(select(func.count()).select_from(ContentPlan)) == 1
        assert session.scalar(select(func.count()).select_from(CalendarEntry)) == 1
        assert session.scalar(select(func.count()).select_from(ContentItem)) == 1
        assert session.scalar(select(func.count()).select_from(MediaAsset)) == 1
        assert session.scalar(select(func.count()).select_from(ContentVersionMedia)) == 1
        assert session.scalar(select(func.count()).select_from(Approval)) == 2
        assert session.scalar(select(func.count()).select_from(Notification)) == 1
        content = session.scalar(select(ContentItem))
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
        association = session.scalar(
            select(ContentVersionMedia).where(
                ContentVersionMedia.content_version_id == content.current_version_id,
                ContentVersionMedia.media_asset_id == asset.id,
            )
        )
        assert association is not None
        image_approval = session.scalar(
            select(Approval).where(Approval.component == ApprovalComponent.IMAGE)
        )
        assert image_approval is not None
        assert association.content_version_id == image_approval.content_version_id
        client = session.scalar(select(User).where(User.email == "client@clinicafeliz.local"))
        assert client is not None
        admin = session.scalar(select(User).where(User.email == "admin@devmark.local"))
        assert admin is not None
        assert client.password_hash != admin.password_hash


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
        assert session.scalar(select(func.count()).select_from(MediaAsset)) == 1
        assert session.scalar(select(func.count()).select_from(ContentVersionMedia)) == 1
        repaired_asset = session.get(MediaAsset, first["media_asset_id"])
        assert repaired_asset is not None
        assert repaired_asset.processing_status == "READY"
        assert repaired_asset.object_key in storage.objects
