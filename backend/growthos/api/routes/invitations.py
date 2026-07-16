from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from growthos.config import Settings, get_settings
from growthos.database import get_session
from growthos.domain.enums import JobStatus
from growthos.models import (
    Business,
    Job,
    Membership,
    Organization,
    OrganizationInvite,
    PasswordResetToken,
    User,
)
from growthos.rate_limit import security_rate_limiter
from growthos.schemas_identity import (
    GenericSecurityResponse,
    InvitationAcceptRequest,
    InvitationAcceptResponse,
    InvitationInspectRequest,
    InvitationInspectResponse,
    PasswordRecoveryRequest,
    PasswordResetRequest,
)
from growthos.security import hash_password, normalize_email
from growthos.services.audit import add_audit_log
from growthos.services.notifications import create_notification
from growthos.services.tokens import (
    TokenPurpose,
    issue_token,
    token_id_from_value,
    verify_token,
)

router = APIRouter()

_GENERIC_RECOVERY_MESSAGE = (
    "Se o e-mail estiver cadastrado, uma mensagem de recuperação será enviada."
)
_INVALID_TOKEN_MESSAGE = "Token inválido, expirado ou já utilizado"


def _database_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _consume_rate_budget(request: Request, settings: Settings, key: str) -> None:
    keys = (f"security:origin:{_client_ip(request)}", f"security:identity:{key}")
    retry_values = [
        retry
        for candidate in keys
        if (
            retry := security_rate_limiter.retry_after(
                candidate,
                attempts=settings.security_rate_limit_attempts,
                window_seconds=settings.security_rate_limit_window_seconds,
            )
        )
        is not None
    ]
    if retry_values:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Muitas tentativas. Aguarde antes de tentar novamente.",
            headers={"Retry-After": str(max(retry_values))},
        )
    for candidate in keys:
        security_rate_limiter.register_failure(
            candidate,
            window_seconds=settings.security_rate_limit_window_seconds,
        )


def _masked_email(email: str) -> str:
    local, separator, domain = email.partition("@")
    if not separator or not local or not domain:
        return "endereço protegido"
    return f"{local[0]}***@{domain}"


def _verified_invite(
    session: Session,
    token: str,
    settings: Settings,
    *,
    lock: bool = False,
) -> OrganizationInvite:
    token_id = token_id_from_value(token)
    if token_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _INVALID_TOKEN_MESSAGE)
    query = select(OrganizationInvite).where(OrganizationInvite.id == token_id)
    if lock:
        query = query.with_for_update()
    invite = session.scalar(query)
    if invite is None or not verify_token(
        token,
        secret=settings.effective_token_secret_key,
        purpose=TokenPurpose.ORGANIZATION_INVITE,
        token_id=invite.id,
        expected_hash=invite.token_hash,
        expires_at=_database_utc(invite.expires_at),
        used_at=_database_utc(invite.accepted_at) if invite.accepted_at else None,
        revoked_at=_database_utc(invite.revoked_at) if invite.revoked_at else None,
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _INVALID_TOKEN_MESSAGE)
    return invite


@router.post("/invitations/inspect", response_model=InvitationInspectResponse)
def inspect_invitation(
    payload: InvitationInspectRequest,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> InvitationInspectResponse:
    token = payload.token.get_secret_value()
    token_id = token_id_from_value(token)
    _consume_rate_budget(request, settings, str(token_id or "invalid"))
    invite = _verified_invite(session, token, settings)
    organization = session.get(Organization, invite.organization_id)
    if organization is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _INVALID_TOKEN_MESSAGE)
    business_name: str | None = None
    if invite.business_id is not None:
        business_name = session.scalar(
            select(Business.name).where(
                Business.id == invite.business_id,
                Business.organization_id == invite.organization_id,
                Business.is_active.is_(True),
            )
        )
        if business_name is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _INVALID_TOKEN_MESSAGE)
    existing_user = session.scalar(select(User.id).where(User.email == invite.email_normalized))
    return InvitationInspectResponse(
        organization=organization,
        business_id=invite.business_id,
        business_name=business_name,
        masked_email=_masked_email(invite.email_normalized),
        role=invite.role,
        expires_at=_database_utc(invite.expires_at),
        requires_account_setup=existing_user is None,
    )


@router.post("/invitations/accept", response_model=InvitationAcceptResponse)
def accept_invitation(
    payload: InvitationAcceptRequest,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> InvitationAcceptResponse:
    token = payload.token.get_secret_value()
    token_id = token_id_from_value(token)
    _consume_rate_budget(request, settings, str(token_id or "invalid"))
    invite = _verified_invite(session, token, settings, lock=True)
    organization = session.get(Organization, invite.organization_id)
    if organization is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _INVALID_TOKEN_MESSAGE)

    user = session.scalar(select(User).where(User.email == invite.email_normalized))
    if user is None:
        if payload.name is None or payload.password is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Nome e senha são necessários para criar a conta",
            )
        user = User(
            email=invite.email_normalized,
            name=payload.name.strip(),
            password_hash=hash_password(payload.password.get_secret_value()),
            is_active=True,
        )
        session.add(user)
        session.flush()
    elif not user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _INVALID_TOKEN_MESSAGE)

    existing_membership = session.scalar(
        select(Membership).where(
            Membership.organization_id == invite.organization_id,
            Membership.user_id == user.id,
        )
    )
    if existing_membership is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este acesso já foi associado")

    membership = Membership(
        organization_id=invite.organization_id,
        user_id=user.id,
        role=invite.role,
        business_id=invite.business_id,
        is_active=True,
    )
    session.add(membership)
    session.flush()
    now = datetime.now(UTC)
    invite.accepted_at = now
    invite.accepted_by_user_id = user.id
    session.execute(
        update(OrganizationInvite)
        .where(
            OrganizationInvite.organization_id == invite.organization_id,
            OrganizationInvite.email_normalized == invite.email_normalized,
            OrganizationInvite.id != invite.id,
            OrganizationInvite.accepted_at.is_(None),
            OrganizationInvite.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    create_notification(
        session,
        organization_id=invite.organization_id,
        business_id=invite.business_id,
        actor_user_id=user.id,
        recipient_user_id=invite.invited_by_user_id,
        notification_type="INVITATION_ACCEPTED",
        title="Convite aceito",
        message="Uma pessoa convidada concluiu o acesso à organização.",
        resource_type="membership",
        resource_id=membership.id,
    )
    add_audit_log(
        session,
        organization_id=invite.organization_id,
        business_id=invite.business_id,
        actor_user_id=user.id,
        action="invitation.accepted",
        resource_type="membership",
        resource_id=membership.id,
        details={"invite_id": str(invite.id), "role": invite.role.value},
    )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Este convite já foi utilizado") from exc
    return InvitationAcceptResponse(
        user=user,
        membership=membership,
        organization=organization,
        accepted_at=now,
    )


@router.post(
    "/password-recovery",
    response_model=GenericSecurityResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_password_recovery(
    payload: PasswordRecoveryRequest,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> GenericSecurityResponse:
    email = normalize_email(payload.email)
    _consume_rate_budget(request, settings, email)
    user = session.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user is not None:
        membership = session.scalar(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.is_active.is_(True),
            )
        )
        if membership is not None:
            now = datetime.now(UTC)
            session.execute(
                update(PasswordResetToken)
                .where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
            reset_id = uuid4()
            issued = issue_token(
                settings.effective_token_secret_key,
                TokenPurpose.PASSWORD_RESET,
                timedelta(minutes=settings.password_reset_ttl_minutes),
                token_id=reset_id,
                now=now,
            )
            reset = PasswordResetToken(
                id=reset_id,
                organization_id=membership.organization_id,
                user_id=user.id,
                token_hash=issued.token_hash,
                expires_at=issued.expires_at,
            )
            session.add(reset)
            session.add(
                Job(
                    organization_id=membership.organization_id,
                    type="identity.password_reset.email",
                    status=JobStatus.PENDING,
                    payload={"reset_id": str(reset.id)},
                    idempotency_key=f"password-reset-email:{reset.id}",
                )
            )
            add_audit_log(
                session,
                organization_id=membership.organization_id,
                actor_user_id=None,
                action="auth.password_recovery_requested",
                resource_type="user",
                resource_id=user.id,
            )
    session.commit()
    return GenericSecurityResponse(message=_GENERIC_RECOVERY_MESSAGE)


@router.post("/password-reset", response_model=GenericSecurityResponse)
def reset_password(
    payload: PasswordResetRequest,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> GenericSecurityResponse:
    token = payload.token.get_secret_value()
    token_id = token_id_from_value(token)
    _consume_rate_budget(request, settings, str(token_id or "invalid"))
    if token_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _INVALID_TOKEN_MESSAGE)
    reset = session.scalar(
        select(PasswordResetToken).where(PasswordResetToken.id == token_id).with_for_update()
    )
    if reset is None or not verify_token(
        token,
        secret=settings.effective_token_secret_key,
        purpose=TokenPurpose.PASSWORD_RESET,
        token_id=reset.id,
        expected_hash=reset.token_hash,
        expires_at=_database_utc(reset.expires_at),
        used_at=_database_utc(reset.used_at) if reset.used_at else None,
        revoked_at=_database_utc(reset.revoked_at) if reset.revoked_at else None,
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _INVALID_TOKEN_MESSAGE)
    user = session.get(User, reset.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _INVALID_TOKEN_MESSAGE)
    now = datetime.now(UTC)
    user.password_hash = hash_password(payload.new_password.get_secret_value())
    user.session_version += 1
    reset.used_at = now
    session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != reset.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    add_audit_log(
        session,
        organization_id=reset.organization_id,
        actor_user_id=user.id,
        action="auth.password_reset",
        resource_type="user",
        resource_id=user.id,
    )
    session.commit()
    return GenericSecurityResponse(message="Senha redefinida. Entre novamente em sua conta.")
