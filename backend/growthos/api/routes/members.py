from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from growthos.config import Settings, get_settings
from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    get_scoped_business,
    require_capability,
    require_csrf,
)
from growthos.domain.enums import BUSINESS_SCOPED_ROLES, JobStatus, Role
from growthos.domain.permissions import Capability, has_capability
from growthos.models import Job, Membership, OrganizationInvite, User
from growthos.schemas import UserRead
from growthos.schemas_identity import (
    InviteStatus,
    MembershipStatus,
    OrganizationInviteCreate,
    OrganizationInviteRead,
    OrganizationMembershipRead,
    OrganizationMembershipUpdate,
)
from growthos.security import normalize_email
from growthos.services.audit import add_audit_log
from growthos.services.tokens import TokenPurpose, issue_token

router = APIRouter()


def _database_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _invite_status(invite: OrganizationInvite) -> InviteStatus:
    if invite.accepted_at is not None:
        return InviteStatus.ACCEPTED
    if invite.revoked_at is not None:
        return InviteStatus.REVOKED
    if _database_utc(invite.expires_at) <= datetime.now(UTC):
        return InviteStatus.EXPIRED
    return InviteStatus.PENDING


def _serialize_invite(invite: OrganizationInvite) -> OrganizationInviteRead:
    return OrganizationInviteRead(
        id=invite.id,
        organization_id=invite.organization_id,
        business_id=invite.business_id,
        email=invite.email_normalized,
        role=invite.role,
        status=_invite_status(invite),
        expires_at=_database_utc(invite.expires_at),
        accepted_at=_database_utc(invite.accepted_at) if invite.accepted_at else None,
        revoked_at=_database_utc(invite.revoked_at) if invite.revoked_at else None,
        invited_by_user_id=invite.invited_by_user_id,
        created_at=_database_utc(invite.created_at),
    )


def _serialize_member(user: User, membership: Membership) -> OrganizationMembershipRead:
    return OrganizationMembershipRead(
        id=membership.id,
        organization_id=membership.organization_id,
        user=UserRead.model_validate(user),
        role=membership.role,
        business_id=membership.business_id,
        status=MembershipStatus.ACTIVE if membership.is_active else MembershipStatus.SUSPENDED,
        invited_by_user_id=None,
        joined_at=membership.created_at,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


def _can_manage_members(context: AuthContext) -> bool:
    return has_capability(context.membership.role, Capability.MEMBERSHIP_MANAGE) or has_capability(
        context.membership.role,
        Capability.CLIENT_MEMBERSHIP_MANAGE,
    )


def _validate_management_scope(
    context: AuthContext,
    *,
    role: Role,
    business_id: UUID | None,
) -> None:
    if role == Role.SUPER_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "SUPER_ADMIN não pode ser concedido aqui")
    if has_capability(context.membership.role, Capability.MEMBERSHIP_MANAGE):
        if role in BUSINESS_SCOPED_ROLES:
            if business_id is None:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Informe a empresa")
        elif business_id is not None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Papéis internos não recebem empresa neste fluxo",
            )
        return
    if not has_capability(context.membership.role, Capability.CLIENT_MEMBERSHIP_MANAGE):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não pode realizar esta ação")
    if role not in {Role.CLIENT_REVIEWER, Role.VIEWER}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Papel não permitido para o gestor cliente")
    if business_id is None or business_id != context.membership.business_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pessoa não encontrada")


@router.get("", response_model=list[OrganizationMembershipRead])
def list_members(
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[OrganizationMembershipRead]:
    require_capability(context, Capability.MEMBERSHIP_VIEW)
    query = (
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.organization_id == context.organization.id)
    )
    if context.membership.role == Role.CLIENT_OWNER:
        query = query.where(
            Membership.business_id == context.membership.business_id,
            Membership.role.in_([Role.CLIENT_OWNER, Role.CLIENT_REVIEWER, Role.VIEWER]),
        )
    return [_serialize_member(user, membership) for user, membership in session.execute(query)]


@router.patch("/{membership_id}", response_model=OrganizationMembershipRead)
def update_member(
    membership_id: UUID,
    payload: OrganizationMembershipUpdate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> OrganizationMembershipRead:
    if not _can_manage_members(context):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não pode realizar esta ação")
    row = session.execute(
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.id == membership_id,
            Membership.organization_id == context.organization.id,
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pessoa não encontrada")
    user, membership = row
    if membership.role == Role.SUPER_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso de plataforma não é editável aqui")
    next_role = payload.role or membership.role
    next_business_id = (
        payload.business_id if "business_id" in payload.model_fields_set else membership.business_id
    )
    if next_role not in BUSINESS_SCOPED_ROLES:
        next_business_id = None
    _validate_management_scope(
        context,
        role=next_role,
        business_id=next_business_id,
    )
    if next_business_id is not None:
        get_scoped_business(session, context, next_business_id)
    next_active = (
        payload.status == MembershipStatus.ACTIVE
        if payload.status is not None
        else membership.is_active
    )
    if membership.user_id == context.user.id and (
        not next_active
        or next_role != membership.role
        or next_business_id != membership.business_id
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Você não pode alterar o próprio acesso")
    if membership.role == Role.AGENCY_ADMIN and (not next_active or next_role != Role.AGENCY_ADMIN):
        active_admins = session.scalar(
            select(func.count(Membership.id)).where(
                Membership.organization_id == context.organization.id,
                Membership.role == Role.AGENCY_ADMIN,
                Membership.is_active.is_(True),
            )
        )
        if active_admins == 1:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "A organização precisa manter ao menos um administrador ativo",
            )
    before = {
        "role": membership.role.value,
        "business_id": str(membership.business_id) if membership.business_id else None,
        "active": membership.is_active,
    }
    fields: list[str] = []
    if membership.role != next_role:
        membership.role = next_role
        fields.append("role")
    if membership.business_id != next_business_id:
        membership.business_id = next_business_id
        fields.append("business_id")
    if membership.is_active != next_active:
        membership.is_active = next_active
        fields.append("status")
    if fields:
        user.session_version += 1
    after = {
        "role": membership.role.value,
        "business_id": str(membership.business_id) if membership.business_id else None,
        "active": membership.is_active,
    }
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=membership.business_id,
        actor_user_id=context.user.id,
        action="membership.updated",
        resource_type="membership",
        resource_id=membership.id,
        details={"fields": fields, "before": before, "after": after},
    )
    session.commit()
    return _serialize_member(user, membership)


@router.get("/invitations", response_model=list[OrganizationInviteRead])
def list_invitations(
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[OrganizationInviteRead]:
    if not (
        has_capability(context.membership.role, Capability.INVITATION_MANAGE)
        or has_capability(context.membership.role, Capability.CLIENT_INVITATION_MANAGE)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não pode consultar convites")
    query = select(OrganizationInvite).where(
        OrganizationInvite.organization_id == context.organization.id
    )
    if context.membership.role == Role.CLIENT_OWNER:
        query = query.where(OrganizationInvite.business_id == context.membership.business_id)
    invites = session.scalars(query.order_by(OrganizationInvite.created_at.desc())).all()
    return [_serialize_invite(invite) for invite in invites]


@router.post(
    "/invitations",
    response_model=OrganizationInviteRead,
    status_code=status.HTTP_201_CREATED,
)
def create_invitation(
    payload: OrganizationInviteCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> OrganizationInviteRead:
    has_agency_scope = has_capability(context.membership.role, Capability.INVITATION_MANAGE)
    has_client_scope = has_capability(
        context.membership.role,
        Capability.CLIENT_INVITATION_MANAGE,
    )
    if not (has_agency_scope or has_client_scope):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não pode criar convites")
    _validate_management_scope(context, role=payload.role, business_id=payload.business_id)
    if payload.business_id is not None:
        get_scoped_business(session, context, payload.business_id)
    email = normalize_email(payload.email)
    existing_membership = session.scalar(
        select(Membership.id)
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.organization_id == context.organization.id,
            User.email == email,
        )
    )
    if existing_membership is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta pessoa já pertence à organização")
    pending = session.scalar(
        select(OrganizationInvite).where(
            OrganizationInvite.organization_id == context.organization.id,
            OrganizationInvite.email_normalized == email,
            OrganizationInvite.accepted_at.is_(None),
            OrganizationInvite.revoked_at.is_(None),
            OrganizationInvite.expires_at > datetime.now(UTC),
        )
    )
    if pending is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um convite pendente")
    invite_id = uuid4()
    issued = issue_token(
        settings.effective_token_secret_key,
        TokenPurpose.ORGANIZATION_INVITE,
        timedelta(hours=settings.invitation_ttl_hours),
        token_id=invite_id,
    )
    invite = OrganizationInvite(
        id=invite_id,
        organization_id=context.organization.id,
        business_id=payload.business_id,
        email_normalized=email,
        invited_name=payload.name.strip(),
        role=payload.role,
        token_hash=issued.token_hash,
        expires_at=issued.expires_at,
        invited_by_user_id=context.user.id,
    )
    session.add(invite)
    session.add(
        Job(
            organization_id=context.organization.id,
            type="identity.invite.email",
            status=JobStatus.PENDING,
            payload={"invite_id": str(invite.id)},
            idempotency_key=f"invitation-email:{invite.id}",
        )
    )
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=invite.business_id,
        actor_user_id=context.user.id,
        action="invitation.created",
        resource_type="organization_invite",
        resource_id=invite.id,
        details={"role": invite.role.value},
    )
    session.commit()
    return _serialize_invite(invite)


@router.delete("/invitations/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    invite_id: UUID,
    response: Response,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> None:
    del response
    if not (
        has_capability(context.membership.role, Capability.INVITATION_MANAGE)
        or has_capability(context.membership.role, Capability.CLIENT_INVITATION_MANAGE)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não pode revogar convites")
    query = select(OrganizationInvite).where(
        OrganizationInvite.id == invite_id,
        OrganizationInvite.organization_id == context.organization.id,
    )
    if context.membership.role == Role.CLIENT_OWNER:
        query = query.where(OrganizationInvite.business_id == context.membership.business_id)
    invite = session.scalar(query.with_for_update())
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Convite não encontrado")
    if invite.accepted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Convite já aceito")
    if invite.revoked_at is None:
        invite.revoked_at = datetime.now(UTC)
        add_audit_log(
            session,
            organization_id=context.organization.id,
            business_id=invite.business_id,
            actor_user_id=context.user.id,
            action="invitation.revoked",
            resource_type="organization_invite",
            resource_id=invite.id,
        )
        session.commit()
