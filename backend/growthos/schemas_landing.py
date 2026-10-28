import re
from datetime import datetime
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class LandingStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"


class LeadSource(StrEnum):
    LANDING_DEMO = "LANDING_DEMO"
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
    preferred_period: Literal["Manhã", "Tarde", "Sábado", "Sem preferência"]
    heard_from: Literal[
        "INSTAGRAM_POST", "INSTAGRAM_STORY", "INDICACAO", "WHATSAPP_DIRETO", "OUTRO"
    ] = "OUTRO"


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
    landing_status: LandingStatus | None
