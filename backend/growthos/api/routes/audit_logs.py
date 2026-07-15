from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.dependencies import AuthContext, get_current_context, require_role
from growthos.domain.enums import Role
from growthos.models import AuditLog
from growthos.schemas import AuditLogRead

router = APIRouter()


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    business_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[AuditLog]:
    require_role(context, Role.SUPER_ADMIN, Role.AGENCY_ADMIN, Role.VIEWER)
    query = select(AuditLog).where(AuditLog.organization_id == context.organization.id)
    limited_business = context.membership.business_id
    if limited_business is not None:
        query = query.where(AuditLog.business_id == limited_business)
    elif business_id is not None:
        query = query.where(AuditLog.business_id == business_id)
    return list(session.scalars(query.order_by(AuditLog.created_at.desc()).limit(limit)).all())

