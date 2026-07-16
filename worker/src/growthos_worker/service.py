from __future__ import annotations

import logging
import signal
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from growthos_worker.handlers import JobHandler
from growthos_worker.jobs import (
    ClaimedJob,
    JobRepository,
    PermanentJobError,
    RetryableJobError,
)


class JobExecutionTimeout(RetryableJobError):
    pass


@contextmanager
def execution_timeout(seconds: int) -> Iterator[None]:
    def raise_timeout(_signum: int, _frame: Any) -> None:
        raise JobExecutionTimeout("job handler timed out")

    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    signal.signal(signal.SIGALRM, raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        signal.signal(signal.SIGALRM, previous_handler)


class WorkerService:
    def __init__(
        self,
        *,
        repository: JobRepository,
        handlers: Mapping[str, JobHandler],
        worker_id: str,
        batch_size: int,
        timeout_seconds: int,
        retry_base_seconds: int,
        retry_max_seconds: int,
        logger: logging.Logger,
    ) -> None:
        self._repository = repository
        self._handlers = handlers
        self._worker_id = worker_id
        self._batch_size = batch_size
        self._timeout_seconds = timeout_seconds
        self._retry_base_seconds = retry_base_seconds
        self._retry_max_seconds = retry_max_seconds
        self._logger = logger

    def run_once(self) -> int:
        expired = self._repository.expire_exhausted(timeout_seconds=self._timeout_seconds)
        if expired:
            self._logger.warning("exhausted jobs marked failed", extra={"count": expired})
        jobs = self._repository.claim(
            worker_id=self._worker_id,
            batch_size=self._batch_size,
            timeout_seconds=self._timeout_seconds,
        )
        for job in jobs:
            self._process(job)
        return len(jobs)

    def _process(self, job: ClaimedJob) -> None:
        handler = self._handlers.get(job.type)
        if handler is None:
            self._finish_failed(job, f"no handler registered for job type {job.type}")
            return
        try:
            with execution_timeout(self._timeout_seconds):
                handler(job)
        except PermanentJobError as exc:
            self._finish_failed(job, _safe_message(exc))
        except RetryableJobError as exc:
            self._finish_retry_or_failed(job, _safe_message(exc))
        except Exception as exc:  # noqa: BLE001 - fronteira do worker não pode encerrar o loop
            self._logger.exception(
                "unexpected job handler failure",
                extra={"job_id": job.id, "job_type": job.type},
            )
            self._finish_retry_or_failed(job, f"unexpected handler error ({type(exc).__name__})")
        else:
            updated = self._repository.mark_succeeded(job.id, worker_id=self._worker_id)
            self._log_lease_result(job, updated, "SUCCEEDED")

    def _finish_retry_or_failed(self, job: ClaimedJob, error: str) -> None:
        if job.attempts >= job.max_attempts:
            self._finish_failed(job, error)
            return
        exponent = max(0, job.attempts - 1)
        delay = min(self._retry_max_seconds, self._retry_base_seconds * (2**exponent))
        updated = self._repository.mark_retry(
            job.id,
            worker_id=self._worker_id,
            delay_seconds=delay,
            error=error,
        )
        self._log_lease_result(job, updated, "RETRY_SCHEDULED")

    def _finish_failed(self, job: ClaimedJob, error: str) -> None:
        updated = self._repository.mark_failed(job.id, worker_id=self._worker_id, error=error)
        self._log_lease_result(job, updated, "FAILED")

    def _log_lease_result(self, job: ClaimedJob, updated: bool, status: str) -> None:
        level = logging.INFO if updated else logging.WARNING
        self._logger.log(
            level,
            "job state updated" if updated else "job lease lost before state update",
            extra={"job_id": job.id, "job_type": job.type, "status": status},
        )


def _safe_message(error: Exception) -> str:
    return " ".join(str(error).split())[:500]
