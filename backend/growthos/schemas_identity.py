"""Contratos HTTP do domínio de identidade da versão 1.0."""

from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from growthos.domain.enums import BUSINESS_SCOPED_ROLES, Role
from growthos.schemas import EmailValue, MembershipRead, OrganizationRead, UserRead


class IdentityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InviteStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class MembershipStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class OrganizationInviteCreate(IdentityRequest):
    name: str = Field(min_length=2, max_length=160)
    email: EmailValue
    role: Role
    business_id: UUID | None = None

    @model_validator(mode="after")
    def validate_role_scope(self) -> Self:
        if self.role == Role.SUPER_ADMIN:
            raise ValueError("SUPER_ADMIN não pode ser concedido por convite de organização")
        if self.role in BUSINESS_SCOPED_ROLES and self.business_id is None:
            raise ValueError("papel do portal exige uma empresa")
        if self.role not in BUSINESS_SCOPED_ROLES and self.business_id is not None:
            raise ValueError("papel interno não aceita empresa neste contrato")
        return self


class OrganizationInviteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    business_id: UUID | None
    email: EmailValue
    role: Role
    status: InviteStatus
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    invited_by_user_id: UUID
    created_at: datetime


class InvitationInspectRequest(IdentityRequest):
    token: SecretStr = Field(min_length=32, max_length=512)


class InvitationInspectResponse(BaseModel):
    organization: OrganizationRead
    business_id: UUID | None
    business_name: str | None = None
    masked_email: str
    role: Role
    expires_at: datetime
    requires_account_setup: bool


class InvitationAcceptRequest(IdentityRequest):
    token: SecretStr = Field(min_length=32, max_length=512)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    password: SecretStr | None = Field(default=None, min_length=12, max_length=256)

    @model_validator(mode="after")
    def require_complete_account_setup(self) -> Self:
        if (self.name is None) != (self.password is None):
            raise ValueError("nome e senha devem ser informados juntos")
        return self


class InvitationAcceptResponse(BaseModel):
    user: UserRead
    membership: MembershipRead
    organization: OrganizationRead
    accepted_at: datetime
    login_required: bool = True


class PasswordRecoveryRequest(IdentityRequest):
    email: EmailValue


class GenericSecurityResponse(BaseModel):
    message: str


class PasswordResetRequest(IdentityRequest):
    token: SecretStr = Field(min_length=32, max_length=512)
    new_password: SecretStr = Field(min_length=12, max_length=256)


class OrganizationMembershipRead(BaseModel):
    id: UUID
    organization_id: UUID
    user: UserRead
    role: Role
    business_id: UUID | None
    status: MembershipStatus
    invited_by_user_id: UUID | None
    joined_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OrganizationMembershipUpdate(IdentityRequest):
    role: Role | None = None
    business_id: UUID | None = None
    status: MembershipStatus | None = None

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        provided = self.model_fields_set
        if not provided:
            raise ValueError("informe ao menos uma alteração")
        if self.role == Role.SUPER_ADMIN:
            raise ValueError("SUPER_ADMIN não pode ser concedido nesta operação")
        if (
            self.role in BUSINESS_SCOPED_ROLES
            and "business_id" in provided
            and self.business_id is None
        ):
            raise ValueError("papel do portal exige uma empresa")
        if (
            self.role is not None
            and self.role not in BUSINESS_SCOPED_ROLES
            and self.business_id is not None
        ):
            raise ValueError("papel interno não aceita empresa neste contrato")
        return self
