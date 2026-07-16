from datetime import datetime, time
from typing import Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from growthos.domain.enums import (
    NotificationCategory,
    NotificationDeliveryMode,
    NotificationDeliveryStatus,
    NotificationDigestFrequency,
    NotificationDigestStatus,
)


class NotificationCategoryPreferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: NotificationCategory
    delivery_mode: NotificationDeliveryMode = NotificationDeliveryMode.IMMEDIATE
    is_enabled: bool = True


class NotificationPreferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_enabled: bool = True
    timezone: str = Field(default="America/Sao_Paulo", min_length=1, max_length=64)
    digest_time: time = time(hour=9)
    weekly_day: int = Field(default=0, ge=0, le=6)
    categories: list[NotificationCategoryPreferenceInput] = Field(
        min_length=1,
        max_length=len(NotificationCategory),
    )

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        normalized = value.strip()
        try:
            ZoneInfo(normalized)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("timezone deve usar um identificador IANA válido") from exc
        return normalized

    @model_validator(mode="after")
    def validate_unique_categories(self) -> Self:
        categories = [item.category for item in self.categories]
        if len(categories) != len(set(categories)):
            raise ValueError("cada categoria deve aparecer uma única vez")
        return self


class NotificationCategoryPreferenceRead(NotificationCategoryPreferenceInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None


class NotificationPreferenceRead(BaseModel):
    id: UUID | None
    organization_id: UUID
    user_id: UUID
    email_enabled: bool
    timezone: str
    digest_time: time
    weekly_day: int
    revision: int
    categories: list[NotificationCategoryPreferenceRead]
    created_at: datetime | None
    updated_at: datetime | None


class NotificationDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notification_id: UUID | None
    digest_id: UUID | None
    channel: str
    delivery_mode: NotificationDeliveryMode
    status: NotificationDeliveryStatus
    attempt_count: int
    provider: str | None
    last_error_code: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NotificationDigestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    frequency: NotificationDigestFrequency
    period_start: datetime
    period_end: datetime
    status: NotificationDigestStatus
    notification_count: int
    created_at: datetime
    updated_at: datetime
