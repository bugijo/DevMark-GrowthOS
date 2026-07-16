from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.dependencies import AuthContext, get_current_context, get_scoped_business
from growthos.domain.permissions import Capability, has_capability
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
    can_view_organization = has_capability(
        context.membership.role,
        Capability.AUDIT_VIEW_ORGANIZATION,
    )
    can_view_scoped = has_capability(
        context.membership.role,
        Capability.AUDIT_VIEW_SCOPED,
    )
    if not (can_view_organization or can_view_scoped):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não pode realizar esta ação")
    query = select(AuditLog).where(AuditLog.organization_id == context.organization.id)
    limited_business = context.membership.business_id
    if limited_business is not None:
        if business_id is not None:
            get_scoped_business(session, context, business_id)
        query = query.where(AuditLog.business_id == limited_business)
    elif business_id is not None:
        get_scoped_business(session, context, business_id)
        query = query.where(AuditLog.business_id == business_id)
    return list(session.scalars(query.order_by(AuditLog.created_at.desc()).limit(limit)).all())
