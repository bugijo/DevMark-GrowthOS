from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.config import Settings, get_settings
from growthos.database import get_session
from growthos.dependencies import AuthContext, get_current_context, require_csrf
from growthos.models import Membership, Organization, User
from growthos.rate_limit import login_rate_limiter
from growthos.schemas import AuthResponse, LoginRequest
from growthos.security import create_session_token, normalize_email, verify_password
from growthos.services.audit import add_audit_log

router = APIRouter()


def _response(context: AuthContext, csrf_token: str) -> AuthResponse:
    return AuthResponse(
        user=context.user,
        membership=context.membership,
        organization=context.organization,
        csrf_token=csrf_token,
    )


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    normalized_email = normalize_email(payload.email)
    client_ip = request.client.host if request.client is not None else "unknown"
    rate_limit_key = f"{client_ip}\x00{normalized_email}"
    retry_after = login_rate_limiter.retry_after(
        rate_limit_key,
        attempts=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )
    if retry_after is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Muitas tentativas de login. Tente novamente em instantes.",
            headers={"Retry-After": str(retry_after)},
        )

    user = session.scalar(select(User).where(User.email == normalized_email))
    password_valid = verify_password(
        payload.password,
        user.password_hash if user is not None else None,
    )
    if user is None or not user.is_active or not password_valid:
        login_rate_limiter.register_failure(
            rate_limit_key,
            window_seconds=settings.login_rate_limit_window_seconds,
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha inválidos")

    login_rate_limiter.clear(rate_limit_key)

    row = session.execute(
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(Membership.user_id == user.id, Membership.is_active.is_(True))
        .order_by(Membership.created_at)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuário sem acesso ativo")
    membership, organization = row
    token, csrf_token = create_session_token(user, membership, settings)
    same_site = cast(Literal["lax", "strict", "none"], settings.session_cookie_same_site)
    max_age = settings.access_token_ttl_minutes * 60
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=same_site,
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=same_site,
        path="/",
    )
    add_audit_log(
        session,
        organization_id=organization.id,
        actor_user_id=user.id,
        action="auth.login",
        resource_type="user",
        resource_id=user.id,
    )
    session.commit()
    context = AuthContext(user, membership, organization, {"csrf": csrf_token})
    return _response(context, csrf_token)


@router.get("/me", response_model=AuthResponse)
def me(context: AuthContext = Depends(get_current_context)) -> AuthResponse:
    return _response(context, str(context.claims["csrf"]))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> None:
    add_audit_log(
        session,
        organization_id=context.organization.id,
        actor_user_id=context.user.id,
        action="auth.logout",
        resource_type="user",
        resource_id=context.user.id,
    )
    session.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
