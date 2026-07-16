from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MediaAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    business_id: UUID
    kind: str
    storage_provider: str
    display_name: str
    mime_type: str
    byte_size: int
    checksum_sha256: str
    width: int | None
    height: int | None
    origin: str
    processing_status: str
    created_at: datetime


class SignedMediaUrlRead(BaseModel):
    url: str
    expires_at: datetime
