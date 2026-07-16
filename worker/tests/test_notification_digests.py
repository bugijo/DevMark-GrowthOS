from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import time
from email.message import EmailMessage
from types import TracebackType
from typing import Any
from uuid import UUID

import pytest

from growthos_worker.handlers import (
    NotificationDigestEmailHandler,
    SmtpEmailHandler,
)
from growthos_worker.jobs import ClaimedJob, PermanentJobError

ORGANIZATION_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PREFERENCE_ID = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
DIGEST_ID = UUID("ffffffff-ffff-4fff-8fff-ffffffffffff")
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
NOTIFICATION_ID = UUID("22222222-2222-4222-8222-222222222222")


@dataclass
class FakeSmtpConnection:
    messages: list[EmailMessage]

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
        self.messages.append(message)


@dataclass
class FakeSmtpFactory:
    messages: list[EmailMessage] = field(default_factory=list)

    def __call__(self, host: str, port: int, timeout: float) -> FakeSmtpConnection:
        assert host == "mailpit"
        assert port == 1025
        assert timeout > 0
        return FakeSmtpConnection(self.messages)


def digest_job(
    *,
    payload: dict[str, object] | None = None,
    attempts: int = 1,
) -> ClaimedJob:
    return ClaimedJob(
        id="digest-job-1",
        organization_id=str(ORGANIZATION_ID),
        type="notification.digest.prepare",
        payload=payload
        or {
            "preference_id": str(PREFERENCE_ID),
            "preference_revision": 3,
            "frequency": "DAILY",
            "scheduled_for": "2026-07-16T12:30:00+00:00",
        },
        attempts=attempts,
        max_attempts=5,
    )


class ScriptedCursor:
    def __init__(self, database: ScriptedDatabase) -> None:
        self.database = database
        self.query = ""

    def __enter__(self) -> ScriptedCursor:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def execute(self, query: str, parameters: tuple[object, ...]) -> None:
        self.query = query
        self.database.queries.append((query, parameters))

    def fetchone(self) -> dict[str, Any] | None:
        if "FROM notification_preferences AS preference" in self.query:
            return {
                "id": PREFERENCE_ID,
                "revision": 3,
                "timezone": "America/Sao_Paulo",
                "digest_time": time(9, 30),
                "weekly_day": 0,
                "email": "reviewer@example.test",
            }
        if "FROM notification_digests AS digest" in self.query:
            return {
                "id": DIGEST_ID,
                "user_id": USER_ID,
                "status": self.database.digest_status,
                "notification_count": len(self.database.items),
            }
        return None

    def fetchall(self) -> list[dict[str, Any]]:
        if "FROM notifications AS notification" in self.query:
            return self.database.items
        return []


class ScriptedConnection:
    def __init__(self, database: ScriptedDatabase) -> None:
        self.database = database

    def __enter__(self) -> ScriptedConnection:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def cursor(self, *, row_factory: object) -> ScriptedCursor:
        assert row_factory is not None
        return ScriptedCursor(self.database)


@dataclass
class ScriptedDatabase:
    digest_status: str = "PENDING"
    items: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {
                "id": NOTIFICATION_ID,
                "title": "Conteúdo aguardando aprovação",
                "message": "Revise o conteúdo no portal.",
                "created_at": "2026-07-16T10:00:00+00:00",
            }
        ]
    )
    queries: list[tuple[str, tuple[object, ...]]] = field(default_factory=list)

    def connect(self) -> ScriptedConnection:
        return ScriptedConnection(self)


def digest_handler(
    database: ScriptedDatabase,
    smtp_factory: FakeSmtpFactory,
) -> NotificationDigestEmailHandler:
    smtp = SmtpEmailHandler(
        host="mailpit",
        port=1025,
        email_from="no-reply@devmark.local",
        logger=logging.getLogger("test.digest.smtp"),
        smtp_factory=smtp_factory,
    )
    return NotificationDigestEmailHandler(
        connect=database.connect,
        smtp=smtp,
        logger=logging.getLogger("test.digest"),
    )


def test_daily_digest_revalidates_tenant_materializes_slot_and_sends_mailpit_email(
    caplog: pytest.LogCaptureFixture,
) -> None:
    database = ScriptedDatabase()
    smtp_factory = FakeSmtpFactory()
    handler = digest_handler(database, smtp_factory)

    with caplog.at_level(logging.INFO):
        result = handler(digest_job())

    assert result == {"provider": "smtp", "delivered": True}
    assert len(smtp_factory.messages) == 1
    message: EmailMessage = smtp_factory.messages[0]
    assert message["To"] == "reviewer@example.test"
    assert message["Subject"] == "Resumo diário do DevMark GrowthOS"
    assert "Conteúdo aguardando aprovação" in message.get_content()
    assert "reviewer@example.test" not in caplog.text
    assert "Revise o conteúdo no portal" not in caplog.text

    sql = "\n".join(query for query, _parameters in database.queries)
    assert "preference.organization_id = %s" in sql
    assert "membership.organization_id = preference.organization_id" in sql
    assert "category_preference.delivery_mode = %s" in sql
    assert "notification.organization_id = %s" in sql
    assert "membership.business_id = notification.business_id" in sql
    assert "prior_delivery.status = 'DELIVERED'" in sql
    assert "ON CONFLICT (organization_id, user_id, frequency, period_end)" in sql
    assert "ON CONFLICT (organization_id, idempotency_key) DO NOTHING" in sql
    assert "notification.digest_delivery_attempted" in sql
    assert any(
        "notification.digest_delivered" in parameters for _query, parameters in database.queries
    )

    job_insert = next(
        parameters for query, parameters in database.queries if "INSERT INTO jobs" in query
    )
    assert str(PREFERENCE_ID) in {str(value) for value in job_insert}
    assert "DAILY" in job_insert
    assert all(
        "reviewer@example.test" not in str(parameters) for _query, parameters in database.queries
    )


def test_empty_digest_schedules_next_slot_without_sending() -> None:
    database = ScriptedDatabase(items=[])
    smtp_factory = FakeSmtpFactory()

    result = digest_handler(database, smtp_factory)(digest_job())

    assert result == {"provider": "smtp", "delivered": False, "empty": True}
    assert smtp_factory.messages == []
    assert any("INSERT INTO jobs" in query for query, _parameters in database.queries)
    assert not any(
        "INSERT INTO notification_deliveries" in query for query, _parameters in database.queries
    )


def test_delivered_digest_retry_is_idempotent_and_does_not_send_again() -> None:
    database = ScriptedDatabase(digest_status="DELIVERED")
    smtp_factory = FakeSmtpFactory()

    result = digest_handler(database, smtp_factory)(digest_job(attempts=2))

    assert result == {"provider": "smtp", "delivered": True, "idempotent": True}
    assert smtp_factory.messages == []
    assert not any(
        "FROM notifications AS notification" in query for query, _parameters in database.queries
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"preference_id": str(PREFERENCE_ID)},
        {
            "preference_id": str(PREFERENCE_ID),
            "preference_revision": 1,
            "frequency": "MONTHLY",
            "scheduled_for": "2026-07-16T12:30:00+00:00",
        },
        {
            "preference_id": str(PREFERENCE_ID),
            "preference_revision": 1,
            "frequency": "DAILY",
            "scheduled_for": "2026-07-16T12:30:00",
        },
    ],
)
def test_digest_rejects_untrusted_or_malformed_payload(payload: dict[str, object]) -> None:
    handler = digest_handler(ScriptedDatabase(), FakeSmtpFactory())

    with pytest.raises(PermanentJobError, match="payload is invalid"):
        handler(digest_job(payload=payload))
