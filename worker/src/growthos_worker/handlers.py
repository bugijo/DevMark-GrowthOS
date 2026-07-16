from __future__ import annotations

import hashlib
import json
import logging
import smtplib
import time
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Any, Protocol, cast
from urllib.parse import quote
from uuid import UUID

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
                       notification.message
                  FROM notifications AS notification
                  JOIN users AS recipient
                    ON recipient.id = notification.recipient_user_id
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
        return self.smtp.send(
            recipient=str(row["email"]),
            subject=str(row["title"]),
            body=str(row["message"]),
            job_id=job.id,
            organization_id=job.organization_id,
        )


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
        raise RetryableJobError(f"identity database lookup failed ({type(exc).__name__})") from exc
    return cast(Mapping[str, Any] | None, row)
