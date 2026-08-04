from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

KINDS = frozenset({"TEXT", "IMAGE", "EMAIL", "STORAGE", "ORCHESTRATION"})
PROVIDERS = frozenset({"MOCK", "HERMES", "EXTERNAL_FUTURE", "SMTP", "MINIO"})


class ProviderConfigUpdate(BaseModel):
    is_active: bool
    priority: int = Field(ge=0, le=1000)
    fallback_provider: str | None = None
    timeout_seconds: int = Field(ge=1, le=120)
    max_attempts: int = Field(ge=1, le=10)
    test_mode: bool = True
    secret_environment_key: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{2,119}$")

    @field_validator("fallback_provider")
    @classmethod
    def validate_fallback(cls, value: str | None) -> str | None:
        if value is not None and value not in PROVIDERS:
            raise ValueError("fallback_provider inválido")
        return value


class ProviderConfigRead(BaseModel):
    id: UUID | None
    kind: str
    provider: str
    is_active: bool
    is_required: bool
    configured_by_environment: bool
    priority: int
    fallback_provider: str | None
    timeout_seconds: int
    max_attempts: int
    test_mode: bool
    secret_environment_key: str | None
    last_checked_at: datetime | None
    last_status: str
    last_error: str | None


class ProviderTestRead(BaseModel):
    kind: str
    provider: str
    status: str
    checked_at: datetime
    message: str
