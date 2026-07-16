from sqlalchemy.orm import Session

from growthos.domain.enums import JobStatus
from growthos.models import Job, Notification


def enqueue_notification_email(
    session: Session,
    notification: Notification,
    *,
    idempotency_key: str,
) -> None:
    """Enfileira somente a referência; o worker revalida acesso e destinatário."""

    session.flush()
    session.add(
        Job(
            organization_id=notification.organization_id,
            type="notification.email.smtp",
            status=JobStatus.PENDING,
            payload={"notification_id": str(notification.id)},
            idempotency_key=idempotency_key,
        )
    )
