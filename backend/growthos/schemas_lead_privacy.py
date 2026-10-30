import re
from datetime import datetime
from itertools import pairwise
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from growthos.schemas_landing import BusinessLeadRead, HeardFrom, PreferredPeriod

LegalBasis = Literal["CONSENTIMENTO", "PROCEDIMENTOS_PRELIMINARES", "LEGITIMO_INTERESSE"]
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_PHONE = re.compile(r"^\+?[0-9 ()-]{10,20}$")


class LeadPrivacyUpsert(BaseModel):
    """Rascunho do aviso; qualquer edição volta o status para DRAFT."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    controller_name: str = Field(min_length=2, max_length=200)
    privacy_contact: str = Field(min_length=3, max_length=200)
    purpose: str = Field(min_length=10, max_length=2000)
    legal_basis: LegalBasis
    data_categories: list[str] = Field(min_length=1, max_length=10)
    retention_days: int = Field(ge=1, le=730)
    notice_text: str = Field(min_length=50, max_length=8000)

    @field_validator("data_categories")
    @classmethod
    def clean_categories(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values if item.strip()]
        if not cleaned or any(len(item) > 80 for item in cleaned):
            raise ValueError("Informe categorias de até 80 caracteres")
        return cleaned


class LeadPrivacyApproval(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(ge=1)
    acknowledged_not_legal_advice: bool
    note: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def require_acknowledgement(self) -> Self:
        if not self.acknowledged_not_legal_advice:
            raise ValueError(
                "Confirme que a aprovação é do estabelecimento e não substitui revisão jurídica"
            )
        return self


class LeadPrivacyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    business_id: UUID
    status: Literal["DRAFT", "APPROVED"]
    controller_name: str
    privacy_contact: str
    purpose: str
    legal_basis: LegalBasis
    data_categories: list[str]
    retention_days: int
    notice_text: str
    version: int
    approved_at: datetime | None
    approval_note: str
    updated_at: datetime


class PublicPrivacyNotice(BaseModel):
    controller_name: str
    privacy_contact: str
    purpose: str
    legal_basis: LegalBasis
    data_categories: list[str]
    retention_days: int
    notice_text: str
    version: int


class AvailabilitySlot(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    weekday: int = Field(ge=0, le=6, description="0 = segunda-feira")
    start: str
    end: str
    label: str = Field(default="", max_length=80)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if not (_TIME.fullmatch(self.start) and _TIME.fullmatch(self.end)):
            raise ValueError("Use horários no formato HH:MM")
        if self.start >= self.end:
            raise ValueError("O início deve ser antes do fim")
        return self


class AvailabilityUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    slots: list[AvailabilitySlot] = Field(default_factory=list, max_length=42)
    notes: str = Field(default="", max_length=1000)
    confirmed_by_business: bool = False

    @model_validator(mode="after")
    def reject_overlaps(self) -> Self:
        by_day: dict[int, list[AvailabilitySlot]] = {}
        for slot in self.slots:
            by_day.setdefault(slot.weekday, []).append(slot)
        for slots in by_day.values():
            ordered = sorted(slots, key=lambda item: item.start)
            for previous, current in pairwise(ordered):
                if current.start < previous.end:
                    raise ValueError("Há janelas sobrepostas no mesmo dia")
        if self.confirmed_by_business and not self.slots:
            raise ValueError("Não é possível confirmar uma agenda vazia")
        return self


class PublicAvailabilityDay(BaseModel):
    """Dia com atendimento confirmado pelo estabelecimento e os períodos cobertos."""

    weekday: int
    periods: list[Literal["Manhã", "Tarde"]]


class AvailabilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    business_id: UUID
    slots: list[AvailabilitySlot]
    notes: str
    confirmed_by_business: bool
    version: int
    updated_at: datetime | None


class RealLeadRequest(BaseModel):
    """Pedido real pela landing — só aceito com o portão de coleta aberto."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    service_requested: str = Field(min_length=1, max_length=120)
    price_item_label: str = Field(default="", max_length=120)
    preferred_period: PreferredPeriod
    preferred_weekday: int | None = Field(default=None, ge=0, le=6)
    heard_from: HeardFrom = "OUTRO"
    contact_name: str = Field(min_length=2, max_length=120)
    contact_phone: str
    privacy_notice_version: int = Field(ge=1)
    privacy_accepted: bool
    # Campo-isca: invisível para pessoas; robôs costumam preenchê-lo.
    website: str = Field(default="", max_length=200)

    @field_validator("contact_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not _PHONE.fullmatch(value):
            raise ValueError("Telefone inválido")
        return re.sub(r"[^0-9+]", "", value)


class LeadExport(BaseModel):
    """Cópia dos dados de um titular, para atender a pedido de acesso/portabilidade."""

    exported_at: datetime
    business_name: str
    controller_name: str | None
    lead: BusinessLeadRead
    history: list[dict[str, object]]


class LeadRetentionRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dry_run: bool = True


class LeadRetentionResult(BaseModel):
    business_id: UUID
    retention_days: int
    cutoff: datetime
    eligible: int
    anonymized: int
    dry_run: bool
