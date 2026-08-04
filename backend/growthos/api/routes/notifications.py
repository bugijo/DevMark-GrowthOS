from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    require_capability,
    require_csrf,
)
from growthos.domain.enums import BUSINESS_SCOPED_ROLES
from growthos.domain.permissions import Capability
from growthos.models import Notification, NotificationDelivery, NotificationDigest
from growthos.models.base import utcnow
from growthos.schemas import NotificationRead
from growthos.schemas_notifications import (
    NotificationDeliveryRead,
    NotificationDigestRead,
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
)
from growthos.services.audit import add_audit_log
from growthos.services.notification_preferences import (
    read_notification_preference,
    upsert_notification_preference,
)

router = APIRouter()


@router.get("/preferences", response_model=NotificationPreferenceRead)
def get_notification_preferences(
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> NotificationPreferenceRead:
    require_capability(context, Capability.NOTIFICATION_VIEW_OWN)
    return read_notification_preference(
        session,
        organization_id=context.organization.id,
        user_id=context.user.id,
    )


@router.put("/preferences", response_model=NotificationPreferenceRead)
def update_notification_preferences(
    payload: NotificationPreferenceUpdate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> NotificationPreferenceRead:
    require_capability(context, Capability.NOTIFICATION_PREFERENCE_UPDATE_OWN)
    preference = upsert_notification_preference(
        session,
        organization_id=context.organization.id,
        user_id=context.user.id,
        actor_user_id=context.user.id,
        payload=payload,
        business_id=context.membership.business_id,
    )
    session.commit()
    return preference


@router.get("/deliveries", response_model=list[NotificationDeliveryRead])
def list_notification_deliveries(
    limit: int = Query(default=50, ge=1, le=100),
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[NotificationDelivery]:
    require_capability(context, Capability.NOTIFICATION_VIEW_OWN)
    return list(
        session.scalars(
            select(NotificationDelivery)
            .where(
                NotificationDelivery.organization_id == context.organization.id,
                NotificationDelivery.user_id == context.user.id,
            )
            .order_by(NotificationDelivery.created_at.desc())
            .limit(limit)
        ).all()
    )


@router.get("/digests", response_model=list[NotificationDigestRead])
def list_notification_digests(
    limit: int = Query(default=50, ge=1, le=100),
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[NotificationDigest]:
    require_capability(context, Capability.NOTIFICATION_VIEW_OWN)
    return list(
        session.scalars(
            select(NotificationDigest)
            .where(
                NotificationDigest.organization_id == context.organization.id,
                NotificationDigest.user_id == context.user.id,
            )
            .order_by(NotificationDigest.period_end.desc())
            .limit(limit)
        ).all()
    )


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = Query(default=False),
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[Notification]:
    require_capability(context, Capability.NOTIFICATION_VIEW_OWN)
    query = select(Notification).where(
        Notification.organization_id == context.organization.id,
        Notification.recipient_user_id == context.user.id,
    )
    limited_business = context.membership.business_id
    if context.membership.role in BUSINESS_SCOPED_ROLES:
        query = query.where(Notification.business_id == limited_business)
    elif limited_business is not None:
        query = query.where(
            or_(
                Notification.business_id.is_(None),
                Notification.business_id == limited_business,
            )
        )
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    return list(session.scalars(query.order_by(Notification.created_at.desc()).limit(100)).all())


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> Notification:
    require_capability(context, Capability.NOTIFICATION_UPDATE_OWN)
    query = select(Notification).where(
        Notification.id == notification_id,
        Notification.organization_id == context.organization.id,
        Notification.recipient_user_id == context.user.id,
    )
    limited_business = context.membership.business_id
    if context.membership.role in BUSINESS_SCOPED_ROLES:
        query = query.where(Notification.business_id == limited_business)
    elif limited_business is not None:
        query = query.where(
            or_(
                Notification.business_id.is_(None),
                Notification.business_id == limited_business,
            )
        )
    notification = session.scalar(query.with_for_update())
    if notification is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificação não encontrada")
    if notification.read_at is None:
        notification.read_at = utcnow()
        add_audit_log(
            session,
            organization_id=context.organization.id,
            business_id=notification.business_id,
            actor_user_id=context.user.id,
            action="notification.read",
            resource_type="notification",
            resource_id=notification.id,
        )
        session.commit()
    return notification
