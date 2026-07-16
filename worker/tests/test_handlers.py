from __future__ import annotations

import logging
from dataclasses import dataclass, field
from email.message import EmailMessage
from types import TracebackType
from typing import Any
from uuid import UUID

import pytest
from growthos.services.tokens import TokenPurpose, derive_token, hash_token

from growthos_worker.handlers import (
    ConsoleEmailHandler,
    IdentityInviteEmailHandler,
    IdentityPasswordResetEmailHandler,
    MockProviderHandler,
    NotificationEmailHandler,
    SmtpEmailHandler,
    default_handlers,
)
from growthos_worker.jobs import ClaimedJob, PermanentJobError, RetryableJobError

ORGANIZATION_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
INVITE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
RESET_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
NOTIFICATION_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
TOKEN_SECRET = "worker-test-token-secret-with-at-least-thirty-two-bytes"


def job(payload: dict[str, object]) -> ClaimedJob:
    return ClaimedJob(
        id="job-1",
        organization_id="organization-1",
        type="provider.mock",
        payload=payload,
        attempts=1,
        max_attempts=3,
    )


def identity_job(job_type: str, payload: dict[str, object]) -> ClaimedJob:
    return ClaimedJob(
        id="identity-job-1",
        organization_id=str(ORGANIZATION_ID),
        type=job_type,
        payload=payload,
        attempts=1,
        max_attempts=3,
    )


def notification_job(payload: dict[str, object]) -> ClaimedJob:
    return ClaimedJob(
        id="notification-job-1",
        organization_id=str(ORGANIZATION_ID),
        type="notification.email.smtp",
        payload=payload,
        attempts=1,
        max_attempts=3,
    )


@dataclass
class FakeSmtpConnection:
    messages: list[EmailMessage]
    failure: Exception | None = None

    def __enter__(self) -> FakeSmtpConnection:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def send_message(self, message: EmailMessage) -> None:
        if self.failure is not None:
            raise self.failure
        self.messages.append(message)


@dataclass
class FakeSmtpFactory:
    messages: list[EmailMessage] = field(default_factory=list)
    calls: list[tuple[str, int, float]] = field(default_factory=list)
    failure: Exception | None = None

    def __call__(self, host: str, port: int, timeout: float) -> FakeSmtpConnection:
        self.calls.append((host, port, timeout))
        return FakeSmtpConnection(self.messages, self.failure)


class FakeCursor:
    def __init__(self, database: FakeDatabase) -> None:
        self.database = database

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def execute(self, query: str, parameters: tuple[object, ...]) -> None:
        self.database.queries.append((query, parameters))

    def fetchone(self) -> dict[str, Any] | None:
        return self.database.row


class FakeConnection:
    def __init__(self, database: FakeDatabase) -> None:
        self.database = database

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def cursor(self, *, row_factory: object) -> FakeCursor:
        assert row_factory is not None
        return FakeCursor(self.database)


@dataclass
class FakeDatabase:
    row: dict[str, Any] | None
    queries: list[tuple[str, tuple[object, ...]]] = field(default_factory=list)

    def connect(self) -> FakeConnection:
        return FakeConnection(self)


def smtp_handler(factory: FakeSmtpFactory, logger_name: str) -> SmtpEmailHandler:
    return SmtpEmailHandler(
        host="mailpit",
        port=1025,
        email_from="no-reply@devmark.local",
        logger=logging.getLogger(logger_name),
        smtp_factory=factory,
    )


def test_mock_provider_is_deterministic() -> None:
    handler = MockProviderHandler(seed="fixed")

    first = handler(job({"objective": "educar", "channel": "instagram"}))
    second = handler(job({"channel": "instagram", "objective": "educar"}))

    assert first == second
    assert first["provider"] == "mock"


def test_mock_provider_exposes_controlled_failure_modes() -> None:
    handler = MockProviderHandler(seed="fixed")

    with pytest.raises(RetryableJobError, match="temporarily unavailable"):
        handler(job({"mode": "retryable_error"}))
    with pytest.raises(PermanentJobError, match="rejected"):
        handler(job({"mode": "permanent_error"}))


def test_console_email_requires_minimum_payload(caplog: pytest.LogCaptureFixture) -> None:
    handler = ConsoleEmailHandler(logging.getLogger("test.console-email"))

    with pytest.raises(PermanentJobError, match="recipient"):
        handler(job({"subject": "Aprovação pendente"}))

    with caplog.at_level(logging.INFO):
        result = handler(
            job(
                {
                    "to": "client@clinicafeliz.local",
                    "subject": "Aprovação pendente",
                    "text": "Existe um conteúdo para revisão.",
                }
            )
        )

    assert result == {"provider": "console", "delivered": True}
    assert "client@clinicafeliz.local" not in caplog.text


def test_smtp_email_uses_injected_client_and_masks_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    factory = FakeSmtpFactory()
    handler = smtp_handler(factory, "test.smtp-email")

    with caplog.at_level(logging.INFO):
        result = handler(
            job(
                {
                    "to": "client@clinicafeliz.local",
                    "subject": "Mensagem operacional",
                    "text": "Corpo que não deve entrar no log.",
                }
            )
        )

    assert result == {"provider": "smtp", "delivered": True}
    assert factory.calls == [("mailpit", 1025, 10.0)]
    assert len(factory.messages) == 1
    assert factory.messages[0]["To"] == "client@clinicafeliz.local"
    assert "client@clinicafeliz.local" not in caplog.text
    assert "Corpo que não deve entrar no log" not in caplog.text


def test_smtp_failure_is_retryable_without_exposing_message() -> None:
    factory = FakeSmtpFactory(failure=OSError("secret transport detail"))
    handler = smtp_handler(factory, "test.smtp-failure")

    with pytest.raises(RetryableJobError, match=r"smtp delivery failed \(OSError\)") as error:
        handler(
            job(
                {
                    "to": "client@clinicafeliz.local",
                    "subject": "Mensagem operacional",
                    "text": "Conteúdo privado",
                }
            )
        )

    assert "secret transport detail" not in str(error.value)
    assert "Conteúdo privado" not in str(error.value)


def test_notification_email_revalidates_active_tenant_membership_before_smtp(
    caplog: pytest.LogCaptureFixture,
) -> None:
    database = FakeDatabase(
        {
            "id": NOTIFICATION_ID,
            "email": "reviewer@example.com",
            "title": "Conteúdo aguardando revisão",
            "message": "Entre no GrowthOS para decidir.",
        }
    )
    factory = FakeSmtpFactory()
    handler = NotificationEmailHandler(
        connect=database.connect,
        smtp=smtp_handler(factory, "test.notification.smtp"),
        logger=logging.getLogger("test.notification"),
    )

    with caplog.at_level(logging.INFO):
        result = handler(notification_job({"notification_id": str(NOTIFICATION_ID)}))

    assert result == {"provider": "smtp", "delivered": True}
    query, parameters = database.queries[0]
    assert "notification.organization_id = %s" in query
    assert "membership.organization_id = notification.organization_id" in query
    assert "membership.is_active IS TRUE" in query
    assert "membership.business_id = notification.business_id" in query
    assert parameters == (NOTIFICATION_ID, ORGANIZATION_ID)
    assert factory.messages[0]["To"] == "reviewer@example.com"
    assert "reviewer@example.com" not in caplog.text
    assert "Entre no GrowthOS para decidir." not in caplog.text


def test_notification_email_never_sends_after_access_is_unavailable() -> None:
    factory = FakeSmtpFactory()
    handler = NotificationEmailHandler(
        connect=FakeDatabase(None).connect,
        smtp=smtp_handler(factory, "test.notification.suspended"),
        logger=logging.getLogger("test.notification.suspended"),
    )

    with pytest.raises(PermanentJobError, match="unavailable"):
        handler(notification_job({"notification_id": str(NOTIFICATION_ID)}))
    assert factory.messages == []


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"notification_id": "invalid"}, "valid notification_id"),
        (
            {"notification_id": str(NOTIFICATION_ID), "to": "forbidden@example.com"},
            "only notification_id",
        ),
    ],
)
def test_notification_email_rejects_invalid_or_expanded_payload(
    payload: dict[str, object],
    message: str,
) -> None:
    handler = NotificationEmailHandler(
        connect=FakeDatabase(None).connect,
        smtp=smtp_handler(FakeSmtpFactory(), "test.notification.invalid"),
        logger=logging.getLogger("test.notification.invalid"),
    )

    with pytest.raises(PermanentJobError, match=message):
        handler(notification_job(payload))


def test_invitation_email_loads_tenant_record_and_keeps_token_out_of_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    token = derive_token(TOKEN_SECRET, TokenPurpose.ORGANIZATION_INVITE, INVITE_ID)
    database = FakeDatabase(
        {
            "id": INVITE_ID,
            "email_normalized": "invited@example.com",
            "invited_name": "Pessoa Cliente",
            "token_hash": hash_token(token),
        }
    )
    factory = FakeSmtpFactory()
    handler = IdentityInviteEmailHandler(
        connect=database.connect,
        smtp=smtp_handler(factory, "test.invite.smtp"),
        token_secret=TOKEN_SECRET,
        frontend_url="http://localhost:3000",
        logger=logging.getLogger("test.invite"),
    )

    with caplog.at_level(logging.INFO):
        result = handler(identity_job("identity.invite.email", {"invite_id": str(INVITE_ID)}))

    assert result == {"provider": "smtp", "delivered": True}
    query, parameters = database.queries[0]
    assert "invitation.organization_id = %s" in query
    assert parameters == (INVITE_ID, ORGANIZATION_ID)
    body = factory.messages[0].get_content()
    assert f"/convites/aceitar#token={token}" in body
    assert token not in caplog.text
    assert "invited@example.com" not in caplog.text
    assert body.strip() not in caplog.text


def test_password_reset_email_loads_tenant_record_and_uses_fragment() -> None:
    token = derive_token(TOKEN_SECRET, TokenPurpose.PASSWORD_RESET, RESET_ID)
    database = FakeDatabase(
        {
            "id": RESET_ID,
            "token_hash": hash_token(token),
            "email": "account@example.com",
            "name": "Pessoa Usuária",
        }
    )
    factory = FakeSmtpFactory()
    handler = IdentityPasswordResetEmailHandler(
        connect=database.connect,
        smtp=smtp_handler(factory, "test.reset.smtp"),
        token_secret=TOKEN_SECRET,
        frontend_url="https://growthos.example.test/base/",
        logger=logging.getLogger("test.reset"),
    )

    result = handler(identity_job("identity.password_reset.email", {"reset_id": str(RESET_ID)}))

    assert result == {"provider": "smtp", "delivered": True}
    query, parameters = database.queries[0]
    assert "reset.organization_id = %s" in query
    assert parameters == (RESET_ID, ORGANIZATION_ID)
    assert (
        f"https://growthos.example.test/base/redefinir-senha#token={token}"
        in factory.messages[0].get_content()
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"invite_id": "invalid"}, "valid invite_id"),
        ({"invite_id": str(INVITE_ID), "token": "forbidden"}, "only invite_id"),
    ],
)
def test_identity_email_rejects_invalid_or_expanded_job_payload(
    payload: dict[str, object],
    message: str,
) -> None:
    handler = IdentityInviteEmailHandler(
        connect=FakeDatabase(None).connect,
        smtp=smtp_handler(FakeSmtpFactory(), "test.invalid-identity"),
        token_secret=TOKEN_SECRET,
        frontend_url="http://localhost:3000",
        logger=logging.getLogger("test.invalid-identity"),
    )

    with pytest.raises(PermanentJobError, match=message):
        handler(identity_job("identity.invite.email", payload))


def test_identity_email_rejects_missing_or_mismatched_record() -> None:
    unavailable = IdentityInviteEmailHandler(
        connect=FakeDatabase(None).connect,
        smtp=smtp_handler(FakeSmtpFactory(), "test.missing-invite"),
        token_secret=TOKEN_SECRET,
        frontend_url="http://localhost:3000",
        logger=logging.getLogger("test.missing-invite"),
    )
    invalid_fingerprint = IdentityInviteEmailHandler(
        connect=FakeDatabase(
            {
                "id": INVITE_ID,
                "email_normalized": "invited@example.com",
                "invited_name": "Pessoa Cliente",
                "token_hash": "0" * 64,
            }
        ).connect,
        smtp=smtp_handler(FakeSmtpFactory(), "test.invalid-fingerprint"),
        token_secret=TOKEN_SECRET,
        frontend_url="http://localhost:3000",
        logger=logging.getLogger("test.invalid-fingerprint"),
    )

    invitation_job = identity_job("identity.invite.email", {"invite_id": str(INVITE_ID)})
    with pytest.raises(PermanentJobError, match="unavailable"):
        unavailable(invitation_job)
    with pytest.raises(PermanentJobError, match="fingerprint"):
        invalid_fingerprint(invitation_job)


def test_default_handlers_preserve_console_and_mock_and_register_identity() -> None:
    database = FakeDatabase(None)
    handlers = default_handlers(
        logger=logging.getLogger("test.default-handlers"),
        mock_seed="fixed",
        latency_ms=0,
        connect=database.connect,
        email_provider="smtp",
        smtp_host="mailpit",
        smtp_port=1025,
        email_from="no-reply@devmark.local",
        frontend_url="http://localhost:3000",
        token_secret=TOKEN_SECRET,
    )

    assert isinstance(handlers["notification.email.console"], ConsoleEmailHandler)
    assert isinstance(handlers["notification.email.smtp"], NotificationEmailHandler)
    assert isinstance(handlers["SEND_EMAIL"], SmtpEmailHandler)
    assert isinstance(handlers["provider.mock"], MockProviderHandler)
    assert isinstance(handlers["identity.invite.email"], IdentityInviteEmailHandler)
    assert isinstance(
        handlers["identity.password_reset.email"],
        IdentityPasswordResetEmailHandler,
    )
