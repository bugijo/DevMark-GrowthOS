from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from growthos.models import AuditLog


def add_audit_log(
    session: Session,
    *,
    organization_id: UUID,
    actor_user_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID | None,
    business_id: UUID | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        organization_id=organization_id,
        business_id=business_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    )
    session.add(entry)
    return entry

