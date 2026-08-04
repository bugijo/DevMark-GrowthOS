import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from growthos_worker.jobs import ClaimedJob, PermanentJobError, RetryableJobError
from growthos_worker.service import WorkerService


@dataclass
class FakeRepository:
    jobs: list[ClaimedJob]
    transitions: list[tuple[str, str, int | None]] = field(default_factory=list)
    claim_batch_sizes: list[int] = field(default_factory=list)
    cleanup_calls: list[tuple[int, int, int]] = field(default_factory=list)
    cleanup_result: int = 0

    def expire_exhausted(self, *, timeout_seconds: int) -> int:
        return 0

    def cleanup_terminal(
        self,
        *,
        succeeded_retention_days: int,
        failed_retention_days: int,
        batch_size: int,
    ) -> int:
        self.cleanup_calls.append((succeeded_retention_days, failed_retention_days, batch_size))
        return self.cleanup_result

    def claim(self, *, worker_id: str, batch_size: int, timeout_seconds: int) -> list[ClaimedJob]:
        self.claim_batch_sizes.append(batch_size)
        claimed = self.jobs[:batch_size]
        del self.jobs[:batch_size]
        return claimed

    def mark_succeeded(self, job_id: str, *, worker_id: str) -> bool:
        self.transitions.append((job_id, "SUCCEEDED", None))
        return True

    def mark_retry(self, job_id: str, *, worker_id: str, delay_seconds: int, error: str) -> bool:
        self.transitions.append((job_id, "RETRY_SCHEDULED", delay_seconds))
        return True

    def mark_failed(self, job_id: str, *, worker_id: str, error: str) -> bool:
        self.transitions.append((job_id, "FAILED", None))
        return True


def make_job(
    *,
    job_id: str = "job-1",
    attempts: int = 1,
    max_attempts: int = 3,
    type_: str = "test",
) -> ClaimedJob:
    return ClaimedJob(
        id=job_id,
        organization_id="organization-1",
        type=type_,
        payload={},
        attempts=attempts,
        max_attempts=max_attempts,
    )


def service(
    repository: FakeRepository,
    handler: Any,
    *,
    job_type: str = "test",
) -> WorkerService:
    return WorkerService(
        repository=repository,
        handlers={job_type: handler},
        worker_id="worker-test",
        batch_size=10,
        timeout_seconds=1,
        retry_base_seconds=5,
        retry_max_seconds=60,
        logger=logging.getLogger("test.worker"),
    )


def test_successful_job_is_completed() -> None:
    repository = FakeRepository([make_job()])

    processed = service(repository, lambda _job: {"ok": True}).run_once()

    assert processed == 1
    assert repository.transitions == [("job-1", "SUCCEEDED", None)]


def test_retry_uses_exponential_backoff() -> None:
    repository = FakeRepository([make_job(attempts=3, max_attempts=5)])

    def transient(_job: ClaimedJob) -> Mapping[str, Any]:
        raise RetryableJobError("temporary failure")

    service(repository, transient).run_once()

    assert repository.transitions == [("job-1", "RETRY_SCHEDULED", 20)]


def test_retry_limit_and_permanent_error_fail_job() -> None:
    exhausted = FakeRepository([make_job(attempts=3, max_attempts=3)])
    permanent = FakeRepository([make_job()])

    def transient(_job: ClaimedJob) -> Mapping[str, Any]:
        raise RetryableJobError("temporary failure")

    def invalid(_job: ClaimedJob) -> Mapping[str, Any]:
        raise PermanentJobError("invalid payload")

    service(exhausted, transient).run_once()
    service(permanent, invalid).run_once()

    assert exhausted.transitions == [("job-1", "FAILED", None)]
    assert permanent.transitions == [("job-1", "FAILED", None)]


def test_missing_handler_is_permanent_failure() -> None:
    repository = FakeRepository([make_job(type_="unknown")])

    service(repository, lambda _job: {}).run_once()

    assert repository.transitions == [("job-1", "FAILED", None)]


def test_batch_is_claimed_one_job_at_a_time_before_processing() -> None:
    repository = FakeRepository(
        [make_job(job_id="job-1"), make_job(job_id="job-2"), make_job(job_id="job-3")]
    )

    processed = service(repository, lambda _job: {"ok": True}).run_once()

    assert processed == 3
    assert repository.claim_batch_sizes == [1, 1, 1, 1]
    assert repository.transitions == [
        ("job-1", "SUCCEEDED", None),
        ("job-2", "SUCCEEDED", None),
        ("job-3", "SUCCEEDED", None),
    ]


def test_worker_stops_claiming_new_jobs_after_shutdown_request() -> None:
    repository = FakeRepository([make_job(job_id="job-1"), make_job(job_id="job-2")])
    stopping = False

    def request_stop_after_progress() -> None:
        nonlocal stopping
        stopping = True

    worker = WorkerService(
        repository=repository,
        handlers={"test": lambda _job: {"ok": True}},
        worker_id="worker-test",
        batch_size=10,
        timeout_seconds=1,
        retry_base_seconds=5,
        retry_max_seconds=60,
        logger=logging.getLogger("test.worker.shutdown"),
        on_progress=request_stop_after_progress,
        should_stop=lambda: stopping,
    )

    assert worker.run_once() == 1
    assert repository.claim_batch_sizes == [1]
    assert [transition[0] for transition in repository.transitions] == ["job-1"]


def test_terminal_cleanup_is_bounded_and_scheduled() -> None:
    repository = FakeRepository([], cleanup_result=4)
    clock_value = 100.0
    worker = WorkerService(
        repository=repository,
        handlers={},
        worker_id="worker-test",
        batch_size=10,
        timeout_seconds=1,
        retry_base_seconds=5,
        retry_max_seconds=60,
        logger=logging.getLogger("test.worker.cleanup"),
        cleanup_interval_seconds=60,
        cleanup_batch_size=25,
        succeeded_retention_days=7,
        failed_retention_days=30,
        clock=lambda: clock_value,
    )

    worker.run_once()
    worker.run_once()

    assert repository.cleanup_calls == [(7, 30, 25)]
