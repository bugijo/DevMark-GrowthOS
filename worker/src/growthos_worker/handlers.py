from __future__ import annotations

import hashlib
import json
import logging
import smtplib
import time
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any, Protocol, cast
from urllib.parse import quote
from uuid import NAMESPACE_URL, UUID, uuid5

from growthos.domain.enums import NotificationDigestFrequency
from growthos.services.notification_preferences import digest_period_start, next_digest_slot
from growthos.services.tokens import TokenPurpose, derive_token, hashes_match
from psycopg.rows import dict_row

from growthos_worker.jobs import ClaimedJob, PermanentJobError, RetryableJobError

JobHandler = Callable[[ClaimedJob], Mapping[str, Any]]
ConnectionFactory = Callable[[], Any]


class SmtpClient(Protocol):
    def send_message(self, message: EmailMessage) -> Any: ...


SmtpFactory = Callable[[str, int, float], AbstractContextManager[SmtpClient]]


def _default_smtp_factory(
    host: str,
    port: int,
    timeout: float,
) -> AbstractContextManager[SmtpClient]:
    return cast(
        AbstractContextManager[SmtpClient],
        smtplib.SMTP(host=host, port=port, timeout=timeout),
    )


def _masked_email(value: str) -> str:
    local, separator, domain = value.partition("@")
    if not separator or not local or not domain:
        return "invalid-address"
    return f"{local[0]}***@{domain}"


def _valid_email(value: str) -> bool:
    local, separator, domain = value.partition("@")
    return bool(
        separator
        and local
        and domain
        and "." not in {local, domain}
        and not any(character in value for character in "\r\n")
    )


@dataclass(slots=True)
class ConsoleEmailHandler:
    logger: logging.Logger

    def __call__(self, job: ClaimedJob) -> Mapping[str, Any]:
        recipient = str(job.payload.get("to") or job.payload.get("recipient") or "").strip()
        subject = str(job.payload.get("subject") or "").strip()
        body = str(job.payload.get("text") or job.payload.get("body") or "")
        if not recipient or "@" not in recipient:
            raise PermanentJobError("email payload has no valid recipient")
        if not subject:
            raise PermanentJobError("email payload has no subject")
        self.logger.info(
            "console email processed",
            extra={
                "event": "job.email.console",
                "job_id": job.id,
                "organization_id": job.organization_id,
                "recipient": _masked_email(recipient),
                "body_size": len(body),
            },
        )
        return {"provider": "console", "delivered": True}


@dataclass(slots=True)
class SmtpEmailHandler:
    host: str
    port: int
    email_from: str
    logger: logging.Logger
    timeout_seconds: float = 10.0
    smtp_factory: SmtpFactory = field(default=_default_smtp_factory, repr=False)

    def __call__(self, job: ClaimedJob) -> Mapping[str, Any]:
        recipient = str(job.payload.get("to") or job.payload.get("recipient") or "").strip()
        subject = str(job.payload.get("subject") or "").strip()
        body = str(job.payload.get("text") or job.payload.get("body") or "")
        return self.send(
            recipient=recipient,
            subject=subject,
            body=body,
            job_id=job.id,
            organization_id=job.organization_id,
        )

    def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        job_id: str,
        organization_id: str,
    ) -> Mapping[str, Any]:
        if not _valid_email(recipient):
            raise PermanentJobError("email payload has no valid recipient")
        if not subject or any(character in subject for character in "\r\n"):
            raise PermanentJobError("email payload has no valid subject")
        if not _valid_email(self.email_from):
            raise PermanentJobError("smtp sender configuration is invalid")
        if not self.host or self.port <= 0:
            raise PermanentJobError("smtp configuration is incomplete")

        message = EmailMessage()
        message["From"] = self.email_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        try:
            with self.smtp_factory(self.host, self.port, self.timeout_seconds) as smtp:
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise RetryableJobError(f"smtp delivery failed ({type(exc).__name__})") from exc

        self.logger.info(
            "smtp email processed",
            extra={
                "event": "job.email.smtp",
                "job_id": job_id,
                "organization_id": organization_id,
                "recipient": _masked_email(recipient),
            },
        )
        return {"provider": "smtp", "delivered": True}


@dataclass(slots=True)
class NotificationEmailHandler:
    connect: ConnectionFactory = field(repr=False)
    smtp: SmtpEmailHandler
    logger: logging.Logger

    def __call__(self, job: ClaimedJob) -> Mapping[str, Any]:
        notification_id = _payload_uuid(
            job,
            "notification_id",
            job_name="notification email",
        )
        organization_id = _job_organization_uuid(job)
        row = _fetch_one(
            self.connect,
            """
                SELECT notification.id,
                       recipient.email,
                       notification.title,
                       notification.message,
                       delivery.status AS delivery_status,
                       COALESCE(
                           category_preference.delivery_mode,
                           'IMMEDIATE'
                       ) AS current_delivery_mode,
                       CASE
                           WHEN preference.id IS NULL THEN TRUE
                           WHEN preference.email_enabled IS FALSE THEN FALSE
                           WHEN category_preference.id IS NULL THEN TRUE
                           WHEN category_preference.is_enabled IS FALSE THEN FALSE
                           WHEN category_preference.delivery_mode = 'IMMEDIATE' THEN TRUE
                           WHEN category_preference.delivery_mode = 'URGENT_ONLY'
                            AND notification.importance = 'URGENT' THEN TRUE
                           ELSE FALSE
                       END AS email_allowed
                  FROM notifications AS notification
                  JOIN users AS recipient
                    ON recipient.id = notification.recipient_user_id
             LEFT JOIN notification_preferences AS preference
                    ON preference.organization_id = notification.organization_id
                   AND preference.user_id = notification.recipient_user_id
             LEFT JOIN notification_category_preferences AS category_preference
                    ON category_preference.preference_id = preference.id
                   AND category_preference.organization_id = notification.organization_id
                   AND category_preference.user_id = notification.recipient_user_id
                   AND category_preference.category = notification.category
             LEFT JOIN notification_deliveries AS delivery
                    ON delivery.organization_id = notification.organization_id
                   AND delivery.notification_id = notification.id
                   AND delivery.channel = 'EMAIL'
                 WHERE notification.id = %s
                   AND notification.organization_id = %s
                   AND recipient.is_active IS TRUE
                   AND EXISTS (
                       SELECT 1
                         FROM memberships AS membership
                        WHERE membership.user_id = notification.recipient_user_id
                          AND membership.organization_id = notification.organization_id
                          AND membership.is_active IS TRUE
                          AND (
                              notification.business_id IS NULL
                              OR membership.business_id IS NULL
                              OR membership.business_id = notification.business_id
                          )
                   )
            """,
            (notification_id, organization_id),
        )
        if row is None:
            raise PermanentJobError("notification email unavailable")
        if row.get("delivery_status") == "DELIVERED":
            return {"provider": "smtp", "delivered": True, "idempotent": True}
        if row.get("email_allowed", True) is False:
            _skip_notification_delivery(
                self.connect,
                notification_id=notification_id,
                organization_id=organization_id,
                delivery_mode=str(row.get("current_delivery_mode") or "IMMEDIATE"),
                job_id=job.id,
            )
            return {"provider": "none", "delivered": False, "skipped": True}
        _record_notification_delivery_attempt(
            self.connect,
            notification_id=notification_id,
            organization_id=organization_id,
            job_id=job.id,
            attempt=job.attempts,
        )
        try:
            result = self.smtp.send(
                recipient=str(row["email"]),
                subject=str(row["title"]),
                body=str(row["message"]),
                job_id=job.id,
                organization_id=job.organization_id,
            )
        except (PermanentJobError, RetryableJobError) as exc:
            _finish_notification_delivery(
                self.connect,
                notification_id=notification_id,
                organization_id=organization_id,
                job_id=job.id,
                attempt=job.attempts,
                delivered=False,
                error_code=type(exc).__name__,
            )
            raise
        _finish_notification_delivery(
            self.connect,
            notification_id=notification_id,
            organization_id=organization_id,
            job_id=job.id,
            attempt=job.attempts,
            delivered=True,
            error_code=None,
        )
        return result


@dataclass(slots=True)
class IdentityInviteEmailHandler:
    connect: ConnectionFactory = field(repr=False)
    smtp: SmtpEmailHandler
    token_secret: str = field(repr=False)
    frontend_url: str
    logger: logging.Logger

    def __call__(self, job: ClaimedJob) -> Mapping[str, Any]:
        invite_id = _payload_uuid(job, "invite_id")
        organization_id = _job_organization_uuid(job)
        row = _fetch_one(
            self.connect,
            """
                SELECT invitation.id,
                       invitation.email_normalized,
                       invitation.invited_name,
                       invitation.token_hash
                  FROM organization_invites AS invitation
                  JOIN organizations AS organization
                    ON organization.id = invitation.organization_id
                 WHERE invitation.id = %s
                   AND invitation.organization_id = %s
                   AND invitation.accepted_at IS NULL
                   AND invitation.revoked_at IS NULL
                   AND invitation.expires_at > NOW()
            """,
            (invite_id, organization_id),
        )
        if row is None:
            raise PermanentJobError("invitation is unavailable")
        token = derive_token(
            self.token_secret,
            TokenPurpose.ORGANIZATION_INVITE,
            UUID(str(row["id"])),
        )
        if not hashes_match(token, str(row["token_hash"])):
            raise PermanentJobError("invitation token fingerprint is invalid")

        recipient = str(row["email_normalized"])
        invited_name = str(row.get("invited_name") or "Pessoa convidada").strip()
        link = f"{self.frontend_url.rstrip('/')}/convites/aceitar#token={quote(token, safe='')}"
        result = self.smtp.send(
            recipient=recipient,
            subject="Seu convite para o DevMark GrowthOS",
            body=(
                f"Olá, {invited_name}.\n\n"
                "Você recebeu um convite para acessar o DevMark GrowthOS.\n"
                f"Aceite o convite por este link: {link}\n\n"
                "O link é pessoal, expira e pode ser usado somente uma vez."
            ),
            job_id=job.id,
            organization_id=job.organization_id,
        )
        self.logger.info(
            "invitation email processed",
            extra={
                "event": "job.identity.invite_email",
                "job_id": job.id,
                "organization_id": job.organization_id,
                "invite_id": str(invite_id),
                "recipient": _masked_email(recipient),
            },
        )
        return result


@dataclass(slots=True)
class IdentityPasswordResetEmailHandler:
    connect: ConnectionFactory = field(repr=False)
    smtp: SmtpEmailHandler
    token_secret: str = field(repr=False)
    frontend_url: str
    logger: logging.Logger

    def __call__(self, job: ClaimedJob) -> Mapping[str, Any]:
        reset_id = _payload_uuid(job, "reset_id")
        organization_id = _job_organization_uuid(job)
        row = _fetch_one(
            self.connect,
            """
                SELECT reset.id,
                       reset.token_hash,
                       account.email,
                       account.name
                  FROM password_reset_tokens AS reset
                  JOIN users AS account
                    ON account.id = reset.user_id
                   AND account.is_active = TRUE
                  JOIN organizations AS organization
                    ON organization.id = reset.organization_id
                 WHERE reset.id = %s
                   AND reset.organization_id = %s
                   AND reset.used_at IS NULL
                   AND reset.revoked_at IS NULL
                   AND reset.expires_at > NOW()
            """,
            (reset_id, organization_id),
        )
        if row is None:
            raise PermanentJobError("password reset is unavailable")
        token = derive_token(
            self.token_secret,
            TokenPurpose.PASSWORD_RESET,
            UUID(str(row["id"])),
        )
        if not hashes_match(token, str(row["token_hash"])):
            raise PermanentJobError("password reset token fingerprint is invalid")

        recipient = str(row["email"])
        name = str(row.get("name") or "").strip()
        greeting = f"Olá, {name}." if name else "Olá."
        link = f"{self.frontend_url.rstrip('/')}/redefinir-senha#token={quote(token, safe='')}"
        result = self.smtp.send(
            recipient=recipient,
            subject="Redefinição de senha do DevMark GrowthOS",
            body=(
                f"{greeting}\n\n"
                "Recebemos uma solicitação para redefinir sua senha.\n"
                f"Crie uma nova senha por este link: {link}\n\n"
                "O link expira, funciona uma única vez e pode ser ignorado se você não fez "
                "esta solicitação."
            ),
            job_id=job.id,
            organization_id=job.organization_id,
        )
        self.logger.info(
            "password reset email processed",
            extra={
                "event": "job.identity.password_reset_email",
                "job_id": job.id,
                "organization_id": job.organization_id,
                "reset_id": str(reset_id),
                "recipient": _masked_email(recipient),
            },
        )
        return result


@dataclass(slots=True)
class NotificationDigestEmailHandler:
    connect: ConnectionFactory = field(repr=False)
    smtp: SmtpEmailHandler
    logger: logging.Logger

    def __call__(self, job: ClaimedJob) -> Mapping[str, Any]:
        preference_id, preference_revision, frequency, scheduled_for = _digest_payload(job)
        organization_id = _job_organization_uuid(job)
        context = _fetch_one(
            self.connect,
            """
                SELECT preference.id,
                       preference.revision,
                       preference.timezone,
                       preference.digest_time,
                       preference.weekly_day,
                       recipient.email
                  FROM notification_preferences AS preference
                  JOIN users AS recipient
                    ON recipient.id = preference.user_id
                   AND recipient.is_active IS TRUE
                 WHERE preference.id = %s
                   AND preference.organization_id = %s
                   AND preference.revision = %s
                   AND preference.email_enabled IS TRUE
                   AND EXISTS (
                       SELECT 1
                         FROM memberships AS membership
                        WHERE membership.organization_id = preference.organization_id
                          AND membership.user_id = preference.user_id
                          AND membership.is_active IS TRUE
                   )
                   AND EXISTS (
                       SELECT 1
                         FROM notification_category_preferences AS category_preference
                        WHERE category_preference.preference_id = preference.id
                          AND category_preference.organization_id = preference.organization_id
                          AND category_preference.user_id = preference.user_id
                          AND category_preference.delivery_mode = %s
                          AND category_preference.is_enabled IS TRUE
                   )
            """,
            (
                preference_id,
                organization_id,
                preference_revision,
                frequency.value,
            ),
        )
        if context is None:
            raise PermanentJobError("notification digest preference unavailable")

        try:
            period_start = digest_period_start(
                period_end=scheduled_for,
                timezone_name=str(context["timezone"]),
                digest_time=context["digest_time"],
                weekly_day=int(context["weekly_day"]),
                frequency=frequency,
            )
        except ValueError as exc:
            raise PermanentJobError(
                "notification digest slot does not match current preference"
            ) from exc
        next_slot = next_digest_slot(
            now=scheduled_for + timedelta(seconds=1),
            timezone_name=str(context["timezone"]),
            digest_time=context["digest_time"],
            weekly_day=int(context["weekly_day"]),
            frequency=frequency,
        )
        prepared = _prepare_notification_digest(
            self.connect,
            preference_id=preference_id,
            preference_revision=preference_revision,
            organization_id=organization_id,
            frequency=frequency,
            period_start=period_start,
            period_end=scheduled_for,
            next_slot=next_slot,
            job_id=job.id,
            attempt=job.attempts,
        )
        if prepared["status"] == "DELIVERED":
            return {"provider": "smtp", "delivered": True, "idempotent": True}
        if prepared["status"] == "EMPTY":
            return {"provider": "smtp", "delivered": False, "empty": True}

        digest_id = UUID(str(prepared["digest_id"]))
        items = cast(list[Mapping[str, Any]], prepared["items"])
        subject = (
            "Resumo diário do DevMark GrowthOS"
            if frequency == NotificationDigestFrequency.DAILY
            else "Resumo semanal do DevMark GrowthOS"
        )
        body = _render_digest_body(items)
        try:
            result = self.smtp.send(
                recipient=str(context["email"]),
                subject=subject,
                body=body,
                job_id=job.id,
                organization_id=job.organization_id,
            )
        except (PermanentJobError, RetryableJobError) as exc:
            _finish_digest_delivery(
                self.connect,
                digest_id=digest_id,
                organization_id=organization_id,
                job_id=job.id,
                delivered=False,
                error_code=type(exc).__name__,
            )
            raise
        _finish_digest_delivery(
            self.connect,
            digest_id=digest_id,
            organization_id=organization_id,
            job_id=job.id,
            delivered=True,
            error_code=None,
        )
        self.logger.info(
            "notification digest processed",
            extra={
                "event": "job.notification.digest",
                "job_id": job.id,
                "organization_id": job.organization_id,
                "frequency": frequency.value,
                "notification_count": len(items),
            },
        )
        return result


@dataclass(slots=True)
class MockProviderHandler:
    seed: str
    latency_ms: int = 0

    def __call__(self, job: ClaimedJob) -> Mapping[str, Any]:
        mode = str(job.payload.get("mode", "success"))
        if mode == "retryable_error":
            raise RetryableJobError("mock provider temporarily unavailable")
        if mode == "permanent_error":
            raise PermanentJobError("mock provider rejected the request")
        if self.latency_ms:
            time.sleep(self.latency_ms / 1000)
        canonical = json.dumps(job.payload, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(f"{self.seed}:{canonical}".encode()).hexdigest()[:16]
        return {"provider": "mock", "reference": f"mock-{digest}"}


def default_handlers(
    *,
    logger: logging.Logger,
    mock_seed: str,
    latency_ms: int,
    connect: ConnectionFactory | None = None,
    email_provider: str = "console",
    smtp_host: str = "",
    smtp_port: int = 1025,
    email_from: str = "no-reply@devmark.local",
    frontend_url: str = "http://localhost:3000",
    token_secret: str = "",
) -> dict[str, JobHandler]:
    console_email = ConsoleEmailHandler(logger)
    smtp_email = SmtpEmailHandler(smtp_host, smtp_port, email_from, logger)
    selected_email: JobHandler = smtp_email if email_provider == "smtp" else console_email
    provider = MockProviderHandler(seed=mock_seed, latency_ms=latency_ms)
    handlers: dict[str, JobHandler] = {
        "notification.email.console": console_email,
        "notification.email.smtp": (
            NotificationEmailHandler(connect, smtp_email, logger)
            if connect is not None
            else smtp_email
        ),
        "EMAIL_CONSOLE": console_email,
        "SEND_EMAIL": selected_email,
        "provider.mock": provider,
        "PROVIDER_MOCK": provider,
        "GENERATE_CONTENT_MOCK": provider,
    }
    if connect is not None and token_secret:
        handlers["identity.invite.email"] = IdentityInviteEmailHandler(
            connect=connect,
            smtp=smtp_email,
            token_secret=token_secret,
            frontend_url=frontend_url,
            logger=logger,
        )
        handlers["identity.password_reset.email"] = IdentityPasswordResetEmailHandler(
            connect=connect,
            smtp=smtp_email,
            token_secret=token_secret,
            frontend_url=frontend_url,
            logger=logger,
        )
    if connect is not None:
        handlers["notification.digest.prepare"] = NotificationDigestEmailHandler(
            connect=connect,
            smtp=smtp_email,
            logger=logger,
        )
    return handlers


def _payload_uuid(job: ClaimedJob, key: str, *, job_name: str = "identity") -> UUID:
    value = job.payload.get(key)
    if set(job.payload) != {key}:
        raise PermanentJobError(f"{job_name} job payload must contain only {key}")
    try:
        return UUID(str(value))
    except (AttributeError, TypeError, ValueError) as exc:
        raise PermanentJobError(f"{job_name} job payload has no valid {key}") from exc


def _job_organization_uuid(job: ClaimedJob) -> UUID:
    try:
        return UUID(job.organization_id)
    except (AttributeError, ValueError) as exc:
        raise PermanentJobError("identity job has no valid organization") from exc


def _fetch_one(
    connect: ConnectionFactory,
    query: str,
    parameters: tuple[object, ...],
) -> Mapping[str, Any] | None:
    try:
        with connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, parameters)
            row = cursor.fetchone()
    except Exception as exc:
        # Fakes e adaptadores podem usar exceções diferentes; o worker registra
        # somente a classe, nunca SQL, token ou dados pessoais.
        raise RetryableJobError(f"database lookup failed ({type(exc).__name__})") from exc
    return cast(Mapping[str, Any] | None, row)


def _skip_notification_delivery(
    connect: ConnectionFactory,
    *,
    notification_id: UUID,
    organization_id: UUID,
    delivery_mode: str,
    job_id: str,
) -> None:
    delivery_id = uuid5(
        NAMESPACE_URL,
        f"growthos:notification-delivery:{organization_id}:{notification_id}:email",
    )
    audit_id = uuid5(
        NAMESPACE_URL,
        f"growthos:notification-email-skipped:{organization_id}:{job_id}",
    )
    query = """
        WITH notification AS (
            SELECT id,
                   organization_id,
                   business_id,
                   recipient_user_id
              FROM notifications
             WHERE id = %s
               AND organization_id = %s
        ),
        delivery AS (
            INSERT INTO notification_deliveries (
                id,
                organization_id,
                user_id,
                notification_id,
                digest_id,
                channel,
                delivery_mode,
                status,
                attempt_count,
                provider,
                last_error_code,
                job_id,
                sent_at,
                created_at,
                updated_at
            )
            SELECT %s,
                   notification.organization_id,
                   notification.recipient_user_id,
                   notification.id,
                   NULL,
                   'EMAIL',
                   %s,
                   'SKIPPED',
                   0,
                   NULL,
                   'PREFERENCE_CHANGED',
                   %s,
                   NULL,
                   NOW(),
                   NOW()
              FROM notification
            ON CONFLICT (organization_id, notification_id, channel)
            DO UPDATE SET delivery_mode = EXCLUDED.delivery_mode,
                          status = 'SKIPPED',
                          provider = NULL,
                          last_error_code = 'PREFERENCE_CHANGED',
                          job_id = EXCLUDED.job_id,
                          updated_at = NOW()
            RETURNING notification_id
        )
        INSERT INTO audit_logs (
            id,
            organization_id,
            business_id,
            actor_user_id,
            action,
            resource_type,
            resource_id,
            metadata,
            created_at
        )
        SELECT %s,
               notification.organization_id,
               notification.business_id,
               NULL,
               'notification.email_skipped_by_preference',
               'notification',
               notification.id,
               json_build_object(
                   'job_id', %s::text,
                   'delivery_mode', %s::text,
                   'reason', 'PREFERENCE_CHANGED'
               ),
               NOW()
          FROM notification
          JOIN delivery ON delivery.notification_id = notification.id
        ON CONFLICT (id) DO NOTHING
    """
    parameters: tuple[object, ...] = (
        notification_id,
        organization_id,
        delivery_id,
        delivery_mode,
        job_id,
        audit_id,
        job_id,
        delivery_mode,
    )
    try:
        with connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, parameters)
    except Exception as exc:
        raise RetryableJobError(
            f"notification preference skip failed ({type(exc).__name__})"
        ) from exc


def _record_notification_delivery_attempt(
    connect: ConnectionFactory,
    *,
    notification_id: UUID,
    organization_id: UUID,
    job_id: str,
    attempt: int,
) -> None:
    delivery_id = uuid5(
        NAMESPACE_URL,
        f"growthos:notification-delivery:{organization_id}:{notification_id}:email",
    )
    audit_id = uuid5(
        NAMESPACE_URL,
        f"growthos:notification-email:{organization_id}:{job_id}:{attempt}",
    )
    query = """
        WITH notification AS (
            SELECT id,
                   organization_id,
                   business_id,
                   recipient_user_id
              FROM notifications
             WHERE id = %s
               AND organization_id = %s
        ),
        delivery AS (
            INSERT INTO notification_deliveries (
                id,
                organization_id,
                user_id,
                notification_id,
                digest_id,
                channel,
                delivery_mode,
                status,
                attempt_count,
                provider,
                last_error_code,
                job_id,
                sent_at,
                created_at,
                updated_at
            )
            SELECT %s,
                   notification.organization_id,
                   notification.recipient_user_id,
                   notification.id,
                   NULL,
                   'EMAIL',
                   'IMMEDIATE',
                   'PROCESSING',
                   %s,
                   'smtp',
                   NULL,
                   %s,
                   NULL,
                   NOW(),
                   NOW()
              FROM notification
            ON CONFLICT (organization_id, notification_id, channel)
            DO UPDATE SET status = 'PROCESSING',
                          attempt_count = GREATEST(
                              notification_deliveries.attempt_count,
                              EXCLUDED.attempt_count
                          ),
                          provider = 'smtp',
                          last_error_code = NULL,
                          job_id = EXCLUDED.job_id,
                          updated_at = NOW()
            RETURNING id
        )
        INSERT INTO audit_logs (
            id,
            organization_id,
            business_id,
            actor_user_id,
            action,
            resource_type,
            resource_id,
            metadata,
            created_at
        )
        SELECT %s,
               notification.organization_id,
               notification.business_id,
               NULL,
               'notification.email_delivery_attempted',
               'notification',
               notification.id,
               json_build_object(
                   'notification_id', notification.id::text,
                   'job_id', %s::text,
                   'attempt', %s::integer
               ),
               NOW()
          FROM notification
          JOIN delivery ON TRUE
        ON CONFLICT (id) DO NOTHING
    """
    parameters: tuple[object, ...] = (
        notification_id,
        organization_id,
        delivery_id,
        attempt,
        job_id,
        audit_id,
        job_id,
        attempt,
    )
    try:
        with connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, parameters)
    except Exception as exc:
        raise RetryableJobError(
            f"notification delivery audit failed ({type(exc).__name__})"
        ) from exc


def _finish_notification_delivery(
    connect: ConnectionFactory,
    *,
    notification_id: UUID,
    organization_id: UUID,
    job_id: str,
    attempt: int,
    delivered: bool,
    error_code: str | None,
) -> None:
    status = "DELIVERED" if delivered else "FAILED"
    action = "notification.email_delivered" if delivered else "notification.email_failed"
    audit_id = uuid5(
        NAMESPACE_URL,
        f"growthos:notification-email-result:{organization_id}:{job_id}:{attempt}:{status}",
    )
    query = """
        WITH delivery AS (
            UPDATE notification_deliveries
               SET status = %s,
                   provider = 'smtp',
                   last_error_code = %s,
                   sent_at = CASE WHEN %s THEN NOW() ELSE sent_at END,
                   updated_at = NOW()
             WHERE organization_id = %s
               AND notification_id = %s
               AND channel = 'EMAIL'
            RETURNING organization_id, user_id, notification_id
        ),
        notification AS (
            SELECT notification.id,
                   notification.organization_id,
                   notification.business_id
              FROM notifications AS notification
              JOIN delivery
                ON delivery.organization_id = notification.organization_id
               AND delivery.notification_id = notification.id
        )
        INSERT INTO audit_logs (
            id,
            organization_id,
            business_id,
            actor_user_id,
            action,
            resource_type,
            resource_id,
            metadata,
            created_at
        )
        SELECT %s,
               notification.organization_id,
               notification.business_id,
               NULL,
               %s,
               'notification',
               notification.id,
               json_build_object(
                   'job_id', %s::text,
                   'attempt', %s::integer,
                   'status', %s::text
               ),
               NOW()
          FROM notification
        ON CONFLICT (id) DO NOTHING
    """
    parameters: tuple[object, ...] = (
        status,
        error_code,
        delivered,
        organization_id,
        notification_id,
        audit_id,
        action,
        job_id,
        attempt,
        status,
    )
    try:
        with connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, parameters)
    except Exception as exc:
        raise RetryableJobError(
            f"notification delivery result failed ({type(exc).__name__})"
        ) from exc


def _digest_payload(
    job: ClaimedJob,
) -> tuple[UUID, int, NotificationDigestFrequency, datetime]:
    expected = {
        "preference_id",
        "preference_revision",
        "frequency",
        "scheduled_for",
    }
    if set(job.payload) != expected:
        raise PermanentJobError("notification digest job payload is invalid")
    try:
        preference_id = UUID(str(job.payload["preference_id"]))
        raw_revision = job.payload["preference_revision"]
        if isinstance(raw_revision, bool):
            raise ValueError
        preference_revision = int(cast(int | str, raw_revision))
        if preference_revision < 1:
            raise ValueError
        frequency = NotificationDigestFrequency(str(job.payload["frequency"]))
        scheduled_for = datetime.fromisoformat(str(job.payload["scheduled_for"]))
        if scheduled_for.tzinfo is None or scheduled_for.utcoffset() is None:
            raise ValueError
    except (KeyError, TypeError, ValueError) as exc:
        raise PermanentJobError("notification digest job payload is invalid") from exc
    return preference_id, preference_revision, frequency, scheduled_for.astimezone(UTC)


def _prepare_notification_digest(
    connect: ConnectionFactory,
    *,
    preference_id: UUID,
    preference_revision: int,
    organization_id: UUID,
    frequency: NotificationDigestFrequency,
    period_start: datetime,
    period_end: datetime,
    next_slot: datetime,
    job_id: str,
    attempt: int,
) -> Mapping[str, Any]:
    digest_id = uuid5(
        NAMESPACE_URL,
        f"growthos:notification-digest:{organization_id}:{preference_id}:"
        f"{frequency.value}:{period_end.isoformat()}",
    )
    delivery_id = uuid5(
        NAMESPACE_URL,
        f"growthos:notification-digest-delivery:{digest_id}:email",
    )
    next_idempotency_key = (
        f"notification-digest:{preference_id}:{preference_revision}:"
        f"{frequency.value}:{next_slot.isoformat()}"
    )
    next_job_id = uuid5(
        NAMESPACE_URL,
        f"growthos:job:{organization_id}:{next_idempotency_key}",
    )
    audit_id = uuid5(
        NAMESPACE_URL,
        f"growthos:notification-digest-attempt:{digest_id}:{job_id}:{attempt}",
    )
    try:
        with connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO notification_digests (
                    id,
                    preference_id,
                    organization_id,
                    user_id,
                    frequency,
                    period_start,
                    period_end,
                    status,
                    notification_count,
                    created_at,
                    updated_at
                )
                SELECT %s,
                       preference.id,
                       preference.organization_id,
                       preference.user_id,
                       %s,
                       %s,
                       %s,
                       'PENDING',
                       0,
                       NOW(),
                       NOW()
                  FROM notification_preferences AS preference
                 WHERE preference.id = %s
                   AND preference.organization_id = %s
                   AND preference.revision = %s
                ON CONFLICT (organization_id, user_id, frequency, period_end)
                DO NOTHING
                """,
                (
                    digest_id,
                    frequency.value,
                    period_start,
                    period_end,
                    preference_id,
                    organization_id,
                    preference_revision,
                ),
            )
            cursor.execute(
                """
                SELECT digest.id,
                       digest.user_id,
                       digest.status,
                       digest.notification_count
                  FROM notification_digests AS digest
                 WHERE digest.organization_id = %s
                   AND digest.preference_id = %s
                   AND digest.frequency = %s
                   AND digest.period_end = %s
                 FOR UPDATE
                """,
                (organization_id, preference_id, frequency.value, period_end),
            )
            digest = cursor.fetchone()
            if digest is None:
                raise RuntimeError("digest slot was not materialized")
            if digest["status"] in {"DELIVERED", "EMPTY"}:
                return {
                    "digest_id": digest["id"],
                    "status": digest["status"],
                    "items": [],
                }

            cursor.execute(
                """
                SELECT notification.id,
                       notification.title,
                       notification.message,
                       notification.created_at
                  FROM notifications AS notification
                  JOIN notification_preferences AS preference
                    ON preference.id = %s
                   AND preference.organization_id = notification.organization_id
                   AND preference.user_id = notification.recipient_user_id
                  JOIN notification_category_preferences AS category_preference
                    ON category_preference.preference_id = preference.id
                   AND category_preference.organization_id = notification.organization_id
                   AND category_preference.user_id = notification.recipient_user_id
                   AND category_preference.category = notification.category
                 WHERE notification.organization_id = %s
                   AND notification.recipient_user_id = %s
                   AND notification.created_at > %s
                   AND notification.created_at <= %s
                   AND category_preference.delivery_mode = %s
                   AND category_preference.is_enabled IS TRUE
                   AND NOT EXISTS (
                       SELECT 1
                         FROM notification_deliveries AS prior_delivery
                        WHERE prior_delivery.organization_id = notification.organization_id
                          AND prior_delivery.notification_id = notification.id
                          AND prior_delivery.channel = 'EMAIL'
                          AND prior_delivery.status = 'DELIVERED'
                   )
                   AND EXISTS (
                       SELECT 1
                         FROM memberships AS membership
                        WHERE membership.organization_id = notification.organization_id
                          AND membership.user_id = notification.recipient_user_id
                          AND membership.is_active IS TRUE
                          AND (
                              notification.business_id IS NULL
                              OR membership.business_id IS NULL
                              OR membership.business_id = notification.business_id
                          )
                   )
                 ORDER BY notification.created_at, notification.id
                """,
                (
                    preference_id,
                    organization_id,
                    digest["user_id"],
                    period_start,
                    period_end,
                    frequency.value,
                ),
            )
            items = cast(list[Mapping[str, Any]], cursor.fetchall())
            for item in items:
                item_id = uuid5(
                    NAMESPACE_URL,
                    f"growthos:notification-digest-item:{digest['id']}:{item['id']}",
                )
                cursor.execute(
                    """
                    INSERT INTO notification_digest_items (
                        id,
                        digest_id,
                        notification_id,
                        organization_id,
                        user_id,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (digest_id, notification_id) DO NOTHING
                    """,
                    (
                        item_id,
                        digest["id"],
                        item["id"],
                        organization_id,
                        digest["user_id"],
                    ),
                )
            digest_status = "PENDING" if items else "EMPTY"
            cursor.execute(
                """
                UPDATE notification_digests
                   SET status = %s,
                       notification_count = %s,
                       updated_at = NOW()
                 WHERE id = %s
                   AND organization_id = %s
                """,
                (digest_status, len(items), digest["id"], organization_id),
            )
            if items:
                cursor.execute(
                    """
                    INSERT INTO notification_deliveries (
                        id,
                        organization_id,
                        user_id,
                        notification_id,
                        digest_id,
                        channel,
                        delivery_mode,
                        status,
                        attempt_count,
                        provider,
                        last_error_code,
                        job_id,
                        sent_at,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        %s, %s, %s, NULL, %s, 'EMAIL', %s, 'PROCESSING',
                        %s, 'smtp', NULL, %s, NULL, NOW(), NOW()
                    )
                    ON CONFLICT (organization_id, digest_id, channel)
                    DO UPDATE SET status = 'PROCESSING',
                                  attempt_count = GREATEST(
                                      notification_deliveries.attempt_count,
                                      EXCLUDED.attempt_count
                                  ),
                                  provider = 'smtp',
                                  last_error_code = NULL,
                                  job_id = EXCLUDED.job_id,
                                  updated_at = NOW()
                    """,
                    (
                        delivery_id,
                        organization_id,
                        digest["user_id"],
                        digest["id"],
                        frequency.value,
                        attempt,
                        job_id,
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO audit_logs (
                        id,
                        organization_id,
                        business_id,
                        actor_user_id,
                        action,
                        resource_type,
                        resource_id,
                        metadata,
                        created_at
                    )
                    VALUES (
                        %s, %s, NULL, NULL,
                        'notification.digest_delivery_attempted',
                        'notification_digest',
                        %s,
                        json_build_object(
                            'job_id', %s::text,
                            'attempt', %s::integer,
                            'frequency', %s::text,
                            'notification_count', %s::integer
                        ),
                        NOW()
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        audit_id,
                        organization_id,
                        digest["id"],
                        job_id,
                        attempt,
                        frequency.value,
                        len(items),
                    ),
                )
            cursor.execute(
                """
                INSERT INTO jobs (
                    id,
                    organization_id,
                    type,
                    status,
                    payload,
                    idempotency_key,
                    attempts,
                    max_attempts,
                    available_at,
                    locked_at,
                    locked_by,
                    last_error,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s, %s, 'notification.digest.prepare', 'PENDING',
                    json_build_object(
                        'preference_id', %s::text,
                        'preference_revision', %s::integer,
                        'frequency', %s::text,
                        'scheduled_for', %s::text
                    ),
                    %s, 0, 5, %s, NULL, NULL, NULL, NOW(), NOW()
                )
                ON CONFLICT (organization_id, idempotency_key) DO NOTHING
                """,
                (
                    next_job_id,
                    organization_id,
                    preference_id,
                    preference_revision,
                    frequency.value,
                    next_slot.isoformat(),
                    next_idempotency_key,
                    next_slot,
                ),
            )
            return {
                "digest_id": digest["id"],
                "status": digest_status,
                "items": items,
            }
    except (PermanentJobError, RetryableJobError):
        raise
    except Exception as exc:
        raise RetryableJobError(
            f"notification digest preparation failed ({type(exc).__name__})"
        ) from exc


def _finish_digest_delivery(
    connect: ConnectionFactory,
    *,
    digest_id: UUID,
    organization_id: UUID,
    job_id: str,
    delivered: bool,
    error_code: str | None,
) -> None:
    status = "DELIVERED" if delivered else "FAILED"
    action = "notification.digest_delivered" if delivered else "notification.digest_failed"
    audit_id = uuid5(
        NAMESPACE_URL,
        f"growthos:notification-digest-result:{digest_id}:{job_id}:{status}",
    )
    query = """
        WITH digest AS (
            UPDATE notification_digests
               SET status = %s,
                   updated_at = NOW()
             WHERE id = %s
               AND organization_id = %s
            RETURNING id, organization_id
        ),
        delivery AS (
            UPDATE notification_deliveries
               SET status = %s,
                   provider = 'smtp',
                   last_error_code = %s,
                   sent_at = CASE WHEN %s THEN NOW() ELSE sent_at END,
                   updated_at = NOW()
             WHERE digest_id = %s
               AND organization_id = %s
               AND channel = 'EMAIL'
            RETURNING digest_id
        )
        INSERT INTO audit_logs (
            id,
            organization_id,
            business_id,
            actor_user_id,
            action,
            resource_type,
            resource_id,
            metadata,
            created_at
        )
        SELECT %s,
               digest.organization_id,
               NULL,
               NULL,
               %s,
               'notification_digest',
               digest.id,
               json_build_object('job_id', %s::text, 'status', %s::text),
               NOW()
          FROM digest
          JOIN delivery ON delivery.digest_id = digest.id
        ON CONFLICT (id) DO NOTHING
    """
    parameters: tuple[object, ...] = (
        status,
        digest_id,
        organization_id,
        status,
        error_code,
        delivered,
        digest_id,
        organization_id,
        audit_id,
        action,
        job_id,
        status,
    )
    try:
        with connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, parameters)
    except Exception as exc:
        raise RetryableJobError(
            f"notification digest result failed ({type(exc).__name__})"
        ) from exc


def _render_digest_body(items: list[Mapping[str, Any]]) -> str:
    visible = items[:100]
    lines = [
        f"Você tem {len(items)} atualização(ões) no DevMark GrowthOS.",
        "",
    ]
    for item in visible:
        title = str(item.get("title") or "Atualização")[:240]
        message = str(item.get("message") or "")[:2000]
        lines.extend((f"- {title}", f"  {message}", ""))
    if len(items) > len(visible):
        lines.append(
            f"Há mais {len(items) - len(visible)} atualização(ões). Acesse o portal para ver todas."
        )
    lines.append("Acesse o portal para revisar os detalhes e próximos passos.")
    return "\n".join(lines)
