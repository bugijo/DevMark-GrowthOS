import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from growthos.domain.enums import Role
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
