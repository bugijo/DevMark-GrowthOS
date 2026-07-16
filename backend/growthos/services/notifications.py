from uuid import UUID

from sqlalchemy.orm import Session

from growthos.models import Notification
from growthos.services.audit import add_audit_log


def create_notification(
    session: Session,
    *,
    organization_id: UUID,
    business_id: UUID | None,
    actor_user_id: UUID | None,
    recipient_user_id: UUID,
    notification_type: str,
    title: str,
    message: str,
    resource_type: str,
    resource_id: UUID,
) -> Notification:
    """Cria uma notificação runtime e sua trilha mínima na mesma transação."""

    notification = Notification(
        organization_id=organization_id,
        business_id=business_id,
        recipient_user_id=recipient_user_id,
        type=notification_type,
        title=title,
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    session.add(notification)
    session.flush()
    add_audit_log(
        session,
        organization_id=organization_id,
        business_id=business_id,
        actor_user_id=actor_user_id,
        action="notification.created",
        resource_type="notification",
        resource_id=notification.id,
        details={
            "notification_type": notification_type,
            "target_resource_id": str(resource_id),
            "target_resource_type": resource_type,
        },
    )
    return notification
