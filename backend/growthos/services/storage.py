from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol
from urllib.parse import urlparse

from fastapi import Depends
from minio import Minio
from PIL import Image, UnidentifiedImageError

from growthos.config import Settings, get_settings

_FORMAT_MIME = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}


class InvalidUpload(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    data: bytes
    mime_type: str
    extension: str
    byte_size: int
    checksum_sha256: str
    width: int
    height: int


class StorageProvider(Protocol):
    name: str

    def put(self, object_key: str, data: bytes, content_type: str) -> None: ...

    def signed_get_url(self, object_key: str, expires_seconds: int) -> str: ...

    def delete(self, object_key: str) -> None: ...


class MinioStorageProvider:
    name = "minio"

    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket
        self._internal = _client(settings.s3_endpoint_url, settings)
        self._public = _client(settings.s3_public_endpoint_url, settings)

    def put(self, object_key: str, data: bytes, content_type: str) -> None:
        self._internal.put_object(
            self._bucket,
            object_key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def signed_get_url(self, object_key: str, expires_seconds: int) -> str:
        return self._public.presigned_get_object(
            self._bucket,
            object_key,
            expires=timedelta(seconds=expires_seconds),
        )

    def delete(self, object_key: str) -> None:
        self._internal.remove_object(self._bucket, object_key)


class MemoryStorageProvider:
    """Adaptador de teste sem rede, com a mesma semântica privada."""

    name = "memory"

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put(self, object_key: str, data: bytes, content_type: str) -> None:
        self.objects[object_key] = (data, content_type)

    def signed_get_url(self, object_key: str, expires_seconds: int) -> str:
        if object_key not in self.objects:
            raise FileNotFoundError(object_key)
        return f"https://storage.test/{object_key}?expires={expires_seconds}"

    def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


def validate_image_upload(
    data: bytes,
    *,
    declared_mime: str | None,
    allowed_mime_types: frozenset[str],
    max_bytes: int,
) -> ValidatedUpload:
    if not data:
        raise InvalidUpload("O arquivo está vazio")
    if len(data) > max_bytes:
        raise InvalidUpload("O arquivo excede o limite permitido")
    try:
        with Image.open(io.BytesIO(data)) as inspected:
            inspected.verify()
        with Image.open(io.BytesIO(data)) as source:
            image_format = (source.format or "").upper()
            detected = _FORMAT_MIME.get(image_format)
            if detected is None:
                raise InvalidUpload("Formato de imagem não permitido")
            mime_type, extension = detected
            if mime_type not in allowed_mime_types:
                raise InvalidUpload("Tipo de arquivo não permitido")
            normalized_declared = (declared_mime or "").casefold().split(";", 1)[0]
            if normalized_declared and normalized_declared != mime_type:
                raise InvalidUpload("O conteúdo do arquivo não corresponde ao tipo informado")
            width, height = source.size
            if width < 1 or height < 1 or width * height > 40_000_000:
                raise InvalidUpload("Dimensões de imagem inválidas")
            normalized = _normalize_image(source, image_format)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as exc:
        raise InvalidUpload("Arquivo de imagem inválido") from exc
    if len(normalized) > max_bytes:
        raise InvalidUpload("A imagem normalizada excede o limite permitido")
    return ValidatedUpload(
        data=normalized,
        mime_type=mime_type,
        extension=extension,
        byte_size=len(normalized),
        checksum_sha256=hashlib.sha256(normalized).hexdigest(),
        width=width,
        height=height,
    )


def safe_display_name(filename: str | None, extension: str) -> str:
    raw = (filename or f"imagem.{extension}").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    normalized = re.sub(r"[^\w .()\-]", "_", raw, flags=re.UNICODE).strip(" .")
    return (normalized or f"imagem.{extension}")[:240]


def _normalize_image(source: Image.Image, image_format: str) -> bytes:
    output = io.BytesIO()
    if image_format == "JPEG":
        source.convert("RGB").save(output, format="JPEG", quality=90, optimize=True)
    elif image_format == "PNG":
        mode = source.mode if source.mode in {"RGB", "RGBA", "L", "LA"} else "RGBA"
        source.convert(mode).save(output, format="PNG", optimize=True)
    elif image_format == "WEBP":
        source.convert("RGBA" if "A" in source.getbands() else "RGB").save(
            output,
            format="WEBP",
            quality=90,
            method=6,
        )
    else:
        raise InvalidUpload("Formato de imagem não permitido")
    return output.getvalue()


def _client(endpoint_url: str, settings: Settings) -> Minio:
    parsed = urlparse(endpoint_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Endpoint S3/MinIO inválido")
    return Minio(
        parsed.netloc,
        access_key=settings.s3_access_key_id,
        secret_key=settings.s3_secret_access_key,
        secure=parsed.scheme == "https",
        region=settings.s3_region,
    )


def _configured_storage(settings: Settings) -> StorageProvider:
    if settings.storage_provider != "minio":
        raise ValueError("STORAGE_PROVIDER deve ser minio nesta versão")
    return MinioStorageProvider(settings)


def get_storage_provider(settings: Settings = Depends(get_settings)) -> StorageProvider:
    return _configured_storage(settings)
