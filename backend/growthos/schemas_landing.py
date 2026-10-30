import re
from datetime import datetime
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_WHATSAPP = re.compile(r"^[1-9][0-9]{9,14}$")
PreferredPeriod = Literal["Manhã", "Tarde", "Sábado", "Sem preferência"]
HeardFrom = Literal["INSTAGRAM_POST", "INSTAGRAM_STORY", "INDICACAO", "WHATSAPP_DIRETO", "OUTRO"]


class LandingStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"


class LeadSource(StrEnum):
    LANDING_DEMO = "LANDING_DEMO"
    LANDING_PAGE = "LANDING_PAGE"
    INSTAGRAM_POST = "INSTAGRAM_POST"
    INSTAGRAM_STORY = "INSTAGRAM_STORY"
    INDICACAO = "INDICACAO"
    WHATSAPP_DIRETO = "WHATSAPP_DIRETO"
    OUTRO = "OUTRO"


class BusinessLeadStatus(StrEnum):
    NOVO = "NOVO"
    AGUARDANDO_DADOS = "AGUARDANDO_DADOS"
    HORARIO_OFERTADO = "HORARIO_OFERTADO"
    CONFIRMADO = "CONFIRMADO"
    REALIZADO = "REALIZADO"
    CANCELADO = "CANCELADO"
    NAO_COMPARECEU = "NAO_COMPARECEU"


class PriceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=120)
    price_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    note: str = Field(default="", max_length=200)


class LandingPageUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    slug: str = Field(min_length=3, max_length=80)
    headline: str = Field(min_length=3, max_length=200)
    subheadline: str = Field(default="", max_length=1000)
    cta_label: str = Field(min_length=2, max_length=80)
    address: str = Field(default="", max_length=300)
    contact_channel: str = Field(default="", max_length=160)
    whatsapp_number: str = Field(default="", max_length=32)
    highlights: list[str] = Field(default_factory=list, max_length=8)
    service_options: list[str] = Field(min_length=1, max_length=10)
    price_items: list[PriceItem] = Field(default_factory=list, max_length=12)
    price_disclaimer: str = Field(default="", max_length=500)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if not _SLUG.fullmatch(value):
            raise ValueError("Use apenas letras minúsculas, números e hífens")
        return value

    @field_validator("whatsapp_number")
    @classmethod
    def validate_whatsapp(cls, value: str) -> str:
        digits = re.sub(r"[\s()+-]", "", value)
        if digits and not _WHATSAPP.fullmatch(digits):
            raise ValueError("Informe o WhatsApp com DDI e DDD, só números (ex.: 5516999999999)")
        return digits

    @field_validator("highlights", "service_options")
    @classmethod
    def strip_items(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values if item.strip()]
        if any(len(item) > 160 for item in cleaned):
            raise ValueError("Cada item deve ter até 160 caracteres")
        return cleaned

    @model_validator(mode="after")
    def require_disclaimer_for_prices(self) -> Self:
        labels = [item.label.casefold() for item in self.price_items]
        if len(labels) != len(set(labels)):
            raise ValueError("Os itens de preço devem ter rótulos diferentes")
        if any(item.price_cents is not None for item in self.price_items) and not (
            self.price_disclaimer
        ):
            raise ValueError("Preços exigem um aviso de referência/confirmação")
        return self


class LandingPageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    business_id: UUID
    slug: str
    status: LandingStatus
    headline: str
    subheadline: str
    cta_label: str
    address: str
    contact_channel: str
    whatsapp_number: str
    highlights: list[str]
    service_options: list[str]
    price_items: list[PriceItem]
    price_disclaimer: str
    demo_mode: bool
    version: int
    approved_at: datetime | None
    updated_at: datetime


class PublicLandingRead(BaseModel):
    """Somente o conteúdo aprovado; sem IDs internos de organização ou usuários."""

    model_config = ConfigDict(from_attributes=True)
    slug: str
    business_name: str
    headline: str
    subheadline: str
    cta_label: str
    address: str
    contact_channel: str
    whatsapp_number: str
    highlights: list[str]
    service_options: list[str]
    price_items: list[PriceItem]
    price_disclaimer: str
    demo_mode: bool


class DemoLeadRequest(BaseModel):
    """Pedido demonstrativo: só escolhas fechadas, nenhum campo de dado pessoal.

    `extra="forbid"` faz qualquer tentativa de enviar nome, telefone ou e-mail
    ser rejeitada com 422 em vez de silenciosamente descartada.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    service_requested: str = Field(min_length=1, max_length=120)
    price_item_label: str = Field(default="", max_length=120)
    preferred_period: PreferredPeriod
    # 0 = segunda-feira; só aceito se o estabelecimento confirmou horários nesse dia.
    preferred_weekday: int | None = Field(default=None, ge=0, le=6)
    heard_from: HeardFrom = "OUTRO"


class DemoLeadReceipt(BaseModel):
    reference: UUID
    message: str


class BusinessLeadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source: LeadSource
    service_requested: str = Field(min_length=1, max_length=120)
    price_item_label: str = Field(default="", max_length=120)
    preferred_period: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=1000)


class BusinessLeadUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: BusinessLeadStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)
    next_action: str | None = Field(default=None, max_length=200)
    next_action_due_at: datetime | None = None


class BusinessLeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    business_id: UUID
    source: LeadSource
    status: BusinessLeadStatus
    is_demo: bool
    service_requested: str
    price_item_label: str
    reference_price_cents: int | None
    preferred_period: str
    notes: str
    next_action: str
    next_action_due_at: datetime | None
    contact_name: str | None = None
    contact_phone: str | None = None
    privacy_notice_version: int | None = None
    anonymized_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class BusinessLeadSummary(BaseModel):
    """Visão compacta para acompanhamento (painel e futuramente o Hermes)."""

    business_id: UUID
    total: int
    demo: int
    by_status: dict[str, int]
    by_source: dict[str, int]
    open_without_next_action: int
    overdue_next_actions: int
    awaiting_response: int = 0
    real: int = 0
    whatsapp_clicks_7d: int = 0
    landing_status: LandingStatus | None


class LandingEvent(BaseModel):
    """Evento anônimo da landing; só alimenta contagens diárias agregadas."""

    model_config = ConfigDict(extra="forbid")
    event: Literal["whatsapp_click"]


class BusinessLeadHistoryEntry(BaseModel):
    action: str
    at: datetime
    actor: str
    changes: dict[str, object]
