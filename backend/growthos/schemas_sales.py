import re
from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LeadStage(StrEnum):
    NEW_LEAD = "NEW_LEAD"
    CONTACT_PENDING = "CONTACT_PENDING"
    BRIEFING = "BRIEFING"
    PROPOSAL_PREPARATION = "PROPOSAL_PREPARATION"
    PROPOSAL_SENT = "PROPOSAL_SENT"
    NEGOTIATION = "NEGOTIATION"
    CONTRACTED = "CONTRACTED"
    IN_PRODUCTION = "IN_PRODUCTION"
    DELIVERED = "DELIVERED"
    AFTER_SALES = "AFTER_SALES"


class ServiceClassification(StrEnum):
    IN_SCOPE_LANDING_PAGE = "IN_SCOPE_LANDING_PAGE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class SalesInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=160)
    company: str = Field(default="", max_length=160)
    email: str = Field(default="", max_length=320)
    whatsapp: str = Field(default="", max_length=24)
    business_type: str = Field(default="", max_length=120)
    goal: str = Field(min_length=3, max_length=2000)
    desired_timeline: str = Field(default="", max_length=160)
    additional_info: str = Field(default="", max_length=2000)

    @field_validator("email")
    @classmethod
    def validate_email_if_present(cls, value: str) -> str:
        if value and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Informe um e-mail válido")
        return value.casefold()

    @field_validator("whatsapp")
    @classmethod
    def validate_whatsapp_if_present(cls, value: str) -> str:
        if value and not 10 <= len(re.sub(r"\D", "", value)) <= 15:
            raise ValueError("Informe um WhatsApp com DDD e número")
        return value

    @model_validator(mode="after")
    def require_contact_channel(self) -> Self:
        if not self.email and not self.whatsapp:
            raise ValueError("Informe um e-mail ou WhatsApp para retorno")
        return self


class PublicQuoteRequest(SalesInput):
    privacy_consent: bool
    honeypot: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def require_privacy_consent(self) -> Self:
        if not self.privacy_consent:
            raise ValueError("É necessário aceitar o aviso de privacidade")
        return self


class ManualLeadCreate(SalesInput):
    pass


class LeadStageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: LeadStage


class LeadTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=2, max_length=200)
    due_at: datetime | None = None
    notes: str = Field(default="", max_length=1000)


class LeadTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    lead_id: UUID
    title: str
    due_at: datetime | None
    completed_at: datetime | None
    notes: str
    created_at: datetime


class SalesLeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    source: str
    stage: LeadStage
    service_classification: ServiceClassification
    classification_reason: str
    name: str
    company: str
    email: str
    whatsapp: str
    business_type: str
    goal: str
    desired_timeline: str
    additional_info: str
    privacy_notice_version: str | None
    consented_at: datetime | None
    proposal_draft: str | None
    created_at: datetime
    updated_at: datetime


class PublicQuoteConfig(BaseModel):
    enabled: bool
    privacy_notice_url: str | None = None
    privacy_notice_version: str | None = None


class PublicQuoteReceipt(BaseModel):
    received: bool = True
    reference: UUID


class LeadBriefingRead(BaseModel):
    lead_id: UUID
    brand: str = "DevMarkia"
    requested_service: str = "Landing page comercial"
    scope_reference: str = "Uma página, até cinco seções e um CTA"
    service_classification: ServiceClassification
    classification_reason: str
    client_inputs: dict[str, str]
    missing_before_proposal: list[str]
    ai_used: bool = False


class ProposalDraftRead(BaseModel):
    lead_id: UUID
    status: str = "DRAFT_NOT_SENT"
    body: str
    ai_used: bool = False
