from __future__ import annotations

from collections.abc import Callable
from typing import Any

from psycopg.rows import dict_row

from growthos_worker.jobs import ClaimedJob


class PostgresJobRepository:
    """Fila PostgreSQL com lease e claim atômico por SKIP LOCKED."""

    def __init__(self, connect: Callable[[], Any]) -> None:
        self._connect = connect

    def expire_exhausted(self, *, timeout_seconds: int) -> int:
        query = """
            UPDATE jobs
               SET status = 'FAILED',
                   locked_at = NULL,
                   locked_by = NULL,
                   last_error = 'retry limit exhausted',
                   updated_at = NOW()
             WHERE attempts >= max_attempts
               AND (
                    status IN ('PENDING', 'RETRY_SCHEDULED')
                    OR (
                        status = 'RUNNING'
                        AND locked_at <= NOW() - (%s * INTERVAL '1 second')
                    )
               )
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (timeout_seconds,))
            return int(cursor.rowcount)

    def claim(self, *, worker_id: str, batch_size: int, timeout_seconds: int) -> list[ClaimedJob]:
        query = """
            WITH candidates AS (
                SELECT id
                  FROM jobs
                 WHERE attempts < max_attempts
                   AND (
                        (
                            status IN ('PENDING', 'RETRY_SCHEDULED')
                            AND available_at <= NOW()
                        )
                        OR (
                            status = 'RUNNING'
                            AND locked_at <= NOW() - (%s * INTERVAL '1 second')
                        )
                   )
                 ORDER BY available_at ASC, created_at ASC
                 FOR UPDATE SKIP LOCKED
                 LIMIT %s
            )
            UPDATE jobs AS job
               SET status = 'RUNNING',
                   attempts = job.attempts + 1,
                   locked_at = NOW(),
                   locked_by = %s,
                   last_error = NULL,
                   updated_at = NOW()
              FROM candidates
             WHERE job.id = candidates.id
         RETURNING job.id,
                   job.organization_id,
                   job.type,
                   job.payload,
                   job.attempts,
                   job.max_attempts
        """
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (timeout_seconds, batch_size, worker_id))
            rows = cursor.fetchall()
        return [
            ClaimedJob(
                id=str(row["id"]),
                organization_id=str(row["organization_id"]),
                type=str(row["type"]),
                payload=row["payload"] or {},
                attempts=int(row["attempts"]),
                max_attempts=int(row["max_attempts"]),
            )
            for row in rows
        ]

    def mark_succeeded(self, job_id: str, *, worker_id: str) -> bool:
        return self._finish(
            job_id,
            worker_id=worker_id,
            status="SUCCEEDED",
            error=None,
            delay_seconds=None,
        )

    def mark_retry(self, job_id: str, *, worker_id: str, delay_seconds: int, error: str) -> bool:
        return self._finish(
            job_id,
            worker_id=worker_id,
            status="RETRY_SCHEDULED",
            error=error,
            delay_seconds=delay_seconds,
        )

    def mark_failed(self, job_id: str, *, worker_id: str, error: str) -> bool:
        return self._finish(
            job_id,
            worker_id=worker_id,
            status="FAILED",
            error=error,
            delay_seconds=None,
        )

    def _finish(
        self,
        job_id: str,
        *,
        worker_id: str,
        status: str,
        error: str | None,
        delay_seconds: int | None,
    ) -> bool:
        if delay_seconds is None:
            available_expression = "available_at"
            parameters: tuple[Any, ...] = (status, error, job_id, worker_id)
        else:
            available_expression = "NOW() + (%s * INTERVAL '1 second')"
            parameters = (status, error, delay_seconds, job_id, worker_id)
        query = f"""
            UPDATE jobs
               SET status = %s,
                   available_at = {available_expression},
                   locked_at = NULL,
                   locked_by = NULL,
                   last_error = %s,
                   updated_at = NOW()
             WHERE id = %s
               AND status = 'RUNNING'
               AND locked_by = %s
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, parameters)
            return int(cursor.rowcount) == 1
