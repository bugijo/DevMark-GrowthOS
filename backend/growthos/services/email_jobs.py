from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.domain.enums import (
    JobStatus,
    NotificationDeliveryMode,
    NotificationDeliveryStatus,
    NotificationImportance,
)
from growthos.models import (
    Job,
    Notification,
    NotificationCategoryPreference,
    NotificationDelivery,
    NotificationPreference,
)
from growthos.services.audit import add_audit_log


def enqueue_notification_email(
    session: Session,
    notification: Notification,
    *,
    idempotency_key: str,
) -> None:
    """Aplica a preferência e enfileira só IDs; o worker revalida o tenant."""

    session.flush()
    preference = session.scalar(
        select(NotificationPreference).where(
            NotificationPreference.organization_id == notification.organization_id,
            NotificationPreference.user_id == notification.recipient_user_id,
        )
    )
    category_preference = None
    if preference is not None:
        category_preference = session.scalar(
            select(NotificationCategoryPreference).where(
                NotificationCategoryPreference.preference_id == preference.id,
                NotificationCategoryPreference.organization_id == notification.organization_id,
                NotificationCategoryPreference.user_id == notification.recipient_user_id,
                NotificationCategoryPreference.category == notification.category,
            )
        )

    email_enabled = preference is None or preference.email_enabled
    category_enabled = category_preference is None or category_preference.is_enabled
    mode = (
        category_preference.delivery_mode
        if category_preference is not None
        else NotificationDeliveryMode.IMMEDIATE
    )
    should_enqueue = (
        email_enabled
        and category_enabled
        and (
            mode == NotificationDeliveryMode.IMMEDIATE
            or (
                mode == NotificationDeliveryMode.URGENT_ONLY
                and notification.importance == NotificationImportance.URGENT
            )
        )
    )
    should_digest = mode in {
        NotificationDeliveryMode.DAILY,
        NotificationDeliveryMode.WEEKLY,
    }
    if should_digest and email_enabled and category_enabled:
        add_audit_log(
            session,
            organization_id=notification.organization_id,
            business_id=notification.business_id,
            actor_user_id=None,
            action="notification.email_deferred_to_digest",
            resource_type="notification",
            resource_id=notification.id,
            details={
                "category": notification.category.value,
                "delivery_mode": mode.value,
            },
        )
        return

    delivery = session.scalar(
        select(NotificationDelivery).where(
            NotificationDelivery.organization_id == notification.organization_id,
            NotificationDelivery.notification_id == notification.id,
            NotificationDelivery.channel == "EMAIL",
        )
    )
    if not should_enqueue:
        reason = (
            "PREFERENCE_DISABLED" if not email_enabled or not category_enabled else "NOT_URGENT"
        )
        if delivery is None:
            session.add(
                NotificationDelivery(
                    organization_id=notification.organization_id,
                    user_id=notification.recipient_user_id,
                    notification_id=notification.id,
                    digest_id=None,
                    channel="EMAIL",
                    delivery_mode=mode,
                    status=NotificationDeliveryStatus.SKIPPED,
                    attempt_count=0,
                    last_error_code=reason,
                )
            )
        add_audit_log(
            session,
            organization_id=notification.organization_id,
            business_id=notification.business_id,
            actor_user_id=None,
            action="notification.email_skipped_by_preference",
            resource_type="notification",
            resource_id=notification.id,
            details={
                "category": notification.category.value,
                "delivery_mode": mode.value,
                "reason": reason,
            },
        )
        return

    job = session.scalar(
        select(Job).where(
            Job.organization_id == notification.organization_id,
            Job.idempotency_key == idempotency_key,
        )
    )
    if job is None:
        job = Job(
            organization_id=notification.organization_id,
            type="notification.email.smtp",
            status=JobStatus.PENDING,
            payload={"notification_id": str(notification.id)},
            idempotency_key=idempotency_key,
        )
        session.add(job)
        session.flush()
    if delivery is None:
        session.add(
            NotificationDelivery(
                organization_id=notification.organization_id,
                user_id=notification.recipient_user_id,
                notification_id=notification.id,
                digest_id=None,
                channel="EMAIL",
                delivery_mode=mode,
                status=NotificationDeliveryStatus.PENDING,
                attempt_count=0,
                job_id=str(job.id),
            )
        )
