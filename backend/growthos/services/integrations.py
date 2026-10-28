"""Credenciais de integração somente leitura para agentes como o Hermes.

O token não representa um usuário: ele carrega apenas uma organização e escopos
explícitos. Não há escopo de escrita nesta versão — mensagens, publicações e
mudanças de status continuam exclusivas de humanos autenticados no portal.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from growthos.models import IntegrationToken, Organization
from growthos.services.audit import add_audit_log
from growthos.services.tokens import (
    TokenPurpose,
    hashes_match,
    issue_token,
    token_id_from_value,
)

LEADS_READ = "leads:read"
ALLOWED_SCOPES = frozenset({LEADS_READ})
MAX_TTL = timedelta(days=90)


@dataclass(frozen=True, slots=True)
class IntegrationContext:
    token_id: UUID
    organization_id: UUID
    label: str
    scopes: frozenset[str]


def issue_integration_token(
    session: Session,
    secret: str,
    organization: Organization,
    *,
    label: str,
    scopes: list[str],
    ttl: timedelta,
) -> tuple[IntegrationToken, str]:
    unknown = set(scopes) - ALLOWED_SCOPES
    if not scopes or unknown:
        raise ValueError(f"Escopos inválidos: {sorted(unknown) or 'nenhum'}")
    if not timedelta(0) < ttl <= MAX_TTL:
        raise ValueError("Validade deve ficar entre 1 e 90 dias")
    token_id = uuid4()
    issued = issue_token(secret, TokenPurpose.INTEGRATION_READ, ttl, token_id=token_id)
    row = IntegrationToken(
        id=token_id,
        organization_id=organization.id,
        label=label.strip()[:80],
        scopes=sorted(set(scopes)),
        token_hash=issued.token_hash,
        expires_at=issued.expires_at,
    )
    session.add(row)
    session.flush()
    add_audit_log(
        session,
        organization_id=organization.id,
        actor_user_id=None,
        action="integration_token.issued",
        resource_type="integration_token",
        resource_id=row.id,
        details={
            "label": row.label,
            "scopes": row.scopes,
            "expires_at": row.expires_at.isoformat(),
        },
    )
    session.commit()
    return row, issued.value


def revoke_integration_token(session: Session, token_id: UUID) -> IntegrationToken | None:
    row = session.get(IntegrationToken, token_id)
    if row is None or row.revoked_at is not None:
        return row
    row.revoked_at = datetime.now(UTC)
    add_audit_log(
        session,
        organization_id=row.organization_id,
        actor_user_id=None,
        action="integration_token.revoked",
        resource_type="integration_token",
        resource_id=row.id,
        details={"label": row.label},
    )
    session.commit()
    return row


def authenticate(session: Session, raw_token: str) -> IntegrationContext | None:
    token_id = token_id_from_value(raw_token)
    if token_id is None:
        return None
    row = session.get(IntegrationToken, token_id)
    if row is None or not hashes_match(raw_token, row.token_hash):
        return None
    now = datetime.now(UTC)
    expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
    if row.revoked_at is not None or expires_at <= now:
        return None
    row.last_used_at = now
    session.commit()
    return IntegrationContext(
        token_id=row.id,
        organization_id=row.organization_id,
        label=row.label,
        scopes=frozenset(row.scopes),
    )


def record_read(
    session: Session, context: IntegrationContext, *, resource: str, business_id: UUID | None
) -> None:
    add_audit_log(
        session,
        organization_id=context.organization_id,
        business_id=business_id,
        actor_user_id=None,
        action="integration.read",
        resource_type="integration_token",
        resource_id=context.token_id,
        details={"label": context.label, "resource": resource},
    )
    session.commit()
