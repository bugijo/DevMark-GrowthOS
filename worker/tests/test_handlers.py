import logging

import pytest

from growthos_worker.handlers import ConsoleEmailHandler, MockProviderHandler
from growthos_worker.jobs import ClaimedJob, PermanentJobError, RetryableJobError


def job(payload: dict[str, object]) -> ClaimedJob:
    return ClaimedJob(
        id="job-1",
        organization_id="organization-1",
        type="provider.mock",
        payload=payload,
        attempts=1,
        max_attempts=3,
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
