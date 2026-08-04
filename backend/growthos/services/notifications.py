from uuid import UUID

from sqlalchemy.orm import Session

from growthos.domain.enums import NotificationCategory, NotificationImportance
from growthos.models import Notification
from growthos.services.audit import add_audit_log

_CATEGORY_BY_TYPE = {
    "CONTENT_REVIEW_REQUESTED": NotificationCategory.CONTENT_AWAITING_APPROVAL,
    "CONTENT_DECISION": NotificationCategory.CONTENT_APPROVED,
    "STRATEGY_REVIEW": NotificationCategory.STRATEGY_AWAITING_APPROVAL,
    "STRATEGY_DECISION": NotificationCategory.CONTENT_APPROVED,
    "INVITATION_ACCEPTED": NotificationCategory.INVITATION,
    "PROCESSING_FAILED": NotificationCategory.PROCESSING_FAILED,
    "PUBLICATION_RECORDED": NotificationCategory.PUBLICATION_RECORDED,
    "REPORT_AVAILABLE": NotificationCategory.REPORT_AVAILABLE,
}

_URGENT_CATEGORIES = frozenset(
    {
        NotificationCategory.CONTENT_AWAITING_APPROVAL,
        NotificationCategory.STRATEGY_AWAITING_APPROVAL,
        NotificationCategory.PROCESSING_FAILED,
    }
)


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
    category: NotificationCategory | None = None,
    importance: NotificationImportance | None = None,
) -> Notification:
    """Cria uma notificação runtime e sua trilha mínima na mesma transação."""

    resolved_category = category or _CATEGORY_BY_TYPE.get(
        notification_type,
        NotificationCategory.REPORT_AVAILABLE,
    )
    resolved_importance = importance or (
        NotificationImportance.URGENT
        if resolved_category in _URGENT_CATEGORIES
        else NotificationImportance.NORMAL
    )
    notification = Notification(
        organization_id=organization_id,
        business_id=business_id,
        recipient_user_id=recipient_user_id,
        type=notification_type,
        category=resolved_category,
        importance=resolved_importance,
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
