import hmac
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.config import Settings, get_settings
from growthos.database import get_session
from growthos.domain.enums import BUSINESS_SCOPED_ROLES, Role
from growthos.models import Business, Membership, Organization, User
from growthos.security import InvalidSession, decode_session_token


@dataclass(frozen=True)
class AuthContext:
    user: User
    membership: Membership
    organization: Organization
    claims: dict[str, Any]


def membership_has_active_scope(session: Session, membership: Membership) -> bool:
    """Falha fechado para papéis do portal sem uma empresa ativa e coerente."""
    if membership.role not in BUSINESS_SCOPED_ROLES:
        return True
    if membership.business_id is None:
        return False
    return (
        session.scalar(
            select(Business.id).where(
                Business.id == membership.business_id,
                Business.organization_id == membership.organization_id,
                Business.is_active.is_(True),
            )
        )
        is not None
    )


def get_current_context(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticação necessária")
    try:
        claims = decode_session_token(token, settings)
    except InvalidSession as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    user_id = UUID(claims["sub"])
    membership_id = UUID(claims["mid"])
    organization_id = UUID(claims["org"])
    row = session.execute(
        select(User, Membership, Organization)
        .join(Membership, Membership.user_id == User.id)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(
            User.id == user_id,
            User.is_active.is_(True),
            Membership.id == membership_id,
            Membership.organization_id == organization_id,
            Membership.is_active.is_(True),
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou revogada")
    user, membership, organization = row
    if not membership_has_active_scope(session, membership):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou revogada")
    expected_business = str(membership.business_id) if membership.business_id else None
    if claims.get("role") != membership.role.value or claims.get("business") != expected_business:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão desatualizada")
    return AuthContext(user, membership, organization, claims)


def require_csrf(
    request: Request,
    context: AuthContext = Depends(get_current_context),
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    expected = str(context.claims["csrf"])
    if not x_csrf_token or not cookie_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token CSRF ausente")
    if not (
        hmac.compare_digest(x_csrf_token, expected) and hmac.compare_digest(cookie_token, expected)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token CSRF inválido")
    return context


def require_role(context: AuthContext, *allowed: Role) -> None:
    if context.membership.role not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não pode realizar esta ação")


def get_scoped_business(session: Session, context: AuthContext, business_id: UUID) -> Business:
    business = session.scalar(
        select(Business).where(
            Business.id == business_id,
            Business.organization_id == context.organization.id,
            Business.is_active.is_(True),
        )
    )
    if business is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
    limited_business = context.membership.business_id
    if context.membership.role in BUSINESS_SCOPED_ROLES and limited_business is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
    if limited_business is not None and limited_business != business.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
    return business
