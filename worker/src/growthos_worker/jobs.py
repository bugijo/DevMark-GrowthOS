from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    id: str
    organization_id: str
    type: str
    payload: Mapping[str, Any]
    attempts: int
    max_attempts: int


class JobRepository(Protocol):
    def expire_exhausted(self, *, timeout_seconds: int) -> int: ...

    def claim(
        self, *, worker_id: str, batch_size: int, timeout_seconds: int
    ) -> list[ClaimedJob]: ...

    def mark_succeeded(self, job_id: str, *, worker_id: str) -> bool: ...

    def mark_retry(
        self, job_id: str, *, worker_id: str, delay_seconds: int, error: str
    ) -> bool: ...

    def mark_failed(self, job_id: str, *, worker_id: str, error: str) -> bool: ...


class RetryableJobError(RuntimeError):
    """Falha transitória cuja mensagem já é segura para persistência."""


class PermanentJobError(RuntimeError):
    """Falha definitiva cuja mensagem já é segura para persistência."""
