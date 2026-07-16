import io
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import AuditLog, MediaAsset
from growthos.services.antimalware import (
    AntimalwareUnavailable,
    get_antimalware_provider,
)
from growthos.services.storage import MemoryStorageProvider, get_storage_provider
from tests.conftest import create_identity, csrf_headers, login


@pytest.fixture
def memory_storage(client: TestClient) -> MemoryStorageProvider:
    storage = MemoryStorageProvider()
    client.app.dependency_overrides[get_storage_provider] = lambda: storage
    yield storage
    client.app.dependency_overrides.pop(get_storage_provider, None)


def _png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (64, 32), color=(31, 122, 109)).save(output, format="PNG")
    return output.getvalue()


def _create_business(client: TestClient, headers: dict[str, str], name: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/businesses",
        json={"name": name, "segment": "Veterinária"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_private_media_upload_detects_content_and_returns_short_signed_url(
    client: TestClient,
    memory_storage: MemoryStorageProvider,
) -> None:
    admin = create_identity(
        slug="media-upload",
        email="media-admin@example.com",
        role=Role.AGENCY_ADMIN,
    )
    headers = csrf_headers(login(client, admin))
    business = _create_business(client, headers, "Clínica Mídia")
    uploaded = client.post(
        f"/api/v1/businesses/{business['id']}/media",
        files={"file": ("foto da clínica.png", _png_bytes(), "image/png")},
        data={"kind": "IMAGE"},
        headers=headers,
    )
    assert uploaded.status_code == 201, uploaded.text
    asset = uploaded.json()
    assert asset["mime_type"] == "image/png"
    assert (asset["width"], asset["height"]) == (64, 32)
    assert asset["processing_status"] == "READY"
    assert "object_key" not in asset
    assert len(memory_storage.objects) == 1
    object_key = next(iter(memory_storage.objects))
    assert "foto da clínica" not in object_key
    assert str(admin.organization_id) in object_key

    listed = client.get(f"/api/v1/businesses/{business['id']}/media")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [asset["id"]]
    signed = client.get(f"/api/v1/media/{asset['id']}/download-url")
    assert signed.status_code == 200, signed.text
    assert signed.json()["url"].startswith("https://storage.test/")

    actions = {item["action"] for item in client.get("/api/v1/audit-logs").json()}
    assert "media.uploaded" in actions
    assert "media.signed_url_issued" in actions


def test_upload_rejects_spoofed_or_executable_content(
    client: TestClient,
    memory_storage: MemoryStorageProvider,
) -> None:
    admin = create_identity(
        slug="media-invalid",
        email="media-invalid@example.com",
        role=Role.AGENCY_ADMIN,
    )
    headers = csrf_headers(login(client, admin))
    business = _create_business(client, headers, "Clínica Arquivo Inválido")
    response = client.post(
        f"/api/v1/businesses/{business['id']}/media",
        files={
            "file": (
                "imagem.png",
                b"<svg><script>alert('x')</script></svg>",
                "image/png",
            )
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert memory_storage.objects == {}


def test_antimalware_mock_quarantines_a_valid_image_with_test_signature(
    client: TestClient,
    memory_storage: MemoryStorageProvider,
) -> None:
    admin = create_identity(
        slug="media-quarantine",
        email="media-quarantine@example.com",
        role=Role.AGENCY_ADMIN,
    )
    headers = csrf_headers(login(client, admin))
    business = _create_business(client, headers, "Clínica Quarentena")
    signed_test_file = _png_bytes() + b"GROWTHOS-MALWARE-MOCK"

    response = client.post(
        f"/api/v1/businesses/{business['id']}/media",
        files={"file": ("teste-seguranca.png", signed_test_file, "image/png")},
        headers=headers,
    )

    assert response.status_code == 422
    assert "verificação de segurança" in response.json()["detail"]
    assert len(memory_storage.objects) == 1
    quarantine_key = next(iter(memory_storage.objects))
    assert "/quarantine/" in quarantine_key
    assert memory_storage.objects[quarantine_key][1] == "application/octet-stream"

    with get_session_factory()() as session:
        asset = session.scalar(
            select(MediaAsset).where(
                MediaAsset.organization_id == admin.organization_id,
                MediaAsset.business_id == UUID(business["id"]),
                MediaAsset.processing_status == "REJECTED",
            )
        )
        assert asset is not None
        assert asset.metadata_safe["antimalware"]["verdict"] == "MALICIOUS"
        assert session.scalar(
            select(AuditLog).where(
                AuditLog.organization_id == admin.organization_id,
                AuditLog.action == "media.quarantined",
                AuditLog.resource_id == asset.id,
            )
        )
        asset_id = asset.id

    listed = client.get(f"/api/v1/businesses/{business['id']}/media")
    assert listed.status_code == 200
    assert listed.json() == []
    assert client.get(f"/api/v1/media/{asset_id}/download-url").status_code == 404


def test_antimalware_failure_is_quarantined_and_fails_closed(
    client: TestClient,
    memory_storage: MemoryStorageProvider,
) -> None:
    class UnavailableScanner:
        name = "mock-unavailable"

        def scan(self, *_args: object, **_kwargs: object) -> object:
            raise AntimalwareUnavailable("private scanner detail")

    client.app.dependency_overrides[get_antimalware_provider] = lambda: UnavailableScanner()
    try:
        admin = create_identity(
            slug="media-scan-failure",
            email="media-scan-failure@example.com",
            role=Role.AGENCY_ADMIN,
        )
        headers = csrf_headers(login(client, admin))
        business = _create_business(client, headers, "Clínica Scanner Indisponível")
        response = client.post(
            f"/api/v1/businesses/{business['id']}/media",
            files={"file": ("imagem.png", _png_bytes(), "image/png")},
            headers=headers,
        )
    finally:
        client.app.dependency_overrides.pop(get_antimalware_provider, None)

    assert response.status_code == 503
    assert "private scanner detail" not in response.text
    assert len(memory_storage.objects) == 1
    with get_session_factory()() as session:
        asset = session.scalar(
            select(MediaAsset).where(
                MediaAsset.organization_id == admin.organization_id,
                MediaAsset.business_id == UUID(business["id"]),
                MediaAsset.processing_status == "FAILED",
            )
        )
        assert asset is not None
        assert asset.metadata_safe["antimalware"]["reason_code"] == "SCANNER_UNAVAILABLE"


def test_media_url_is_isolated_between_organizations(
    client: TestClient,
    memory_storage: MemoryStorageProvider,
) -> None:
    first = create_identity(
        slug="media-first",
        email="media-first@example.com",
        role=Role.AGENCY_ADMIN,
    )
    first_headers = csrf_headers(login(client, first))
    business = _create_business(client, first_headers, "Clínica Primeira")
    upload = client.post(
        f"/api/v1/businesses/{business['id']}/media",
        files={"file": ("safe.png", _png_bytes(), "image/png")},
        headers=first_headers,
    )
    assert upload.status_code == 201, upload.text
    asset_id = upload.json()["id"]

    second_client = TestClient(client.app)
    second_client.app.dependency_overrides[get_storage_provider] = lambda: memory_storage
    second = create_identity(
        slug="media-second",
        email="media-second@example.com",
        role=Role.AGENCY_ADMIN,
    )
    login(second_client, second)
    assert second_client.get(f"/api/v1/media/{asset_id}/download-url").status_code == 404
