from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from growthos_worker.jobs import ClaimedJob, PermanentJobError, RetryableJobError

JobHandler = Callable[[ClaimedJob], Mapping[str, Any]]


def _masked_email(value: str) -> str:
    local, separator, domain = value.partition("@")
    if not separator or not local or not domain:
        return "invalid-address"
    return f"{local[0]}***@{domain}"


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
    *, logger: logging.Logger, mock_seed: str, latency_ms: int
) -> dict[str, JobHandler]:
    email = ConsoleEmailHandler(logger)
    provider = MockProviderHandler(seed=mock_seed, latency_ms=latency_ms)
    return {
        "notification.email.console": email,
        "EMAIL_CONSOLE": email,
        "SEND_EMAIL": email,
        "provider.mock": provider,
        "PROVIDER_MOCK": provider,
        "GENERATE_CONTENT_MOCK": provider,
    }
