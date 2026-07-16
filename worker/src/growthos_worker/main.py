from __future__ import annotations

import argparse
import signal
import threading
from pathlib import Path
from typing import Any

import psycopg

from growthos_worker.handlers import default_handlers
from growthos_worker.logging import configure_logging
from growthos_worker.repository import PostgresJobRepository
from growthos_worker.service import WorkerService
from growthos_worker.settings import WorkerSettings


def _validate_backend_contract() -> None:
    import growthos  # noqa: F401 - garante que o backend compartilhado está instalado
    from growthos.models import Job

    expected = {
        "id",
        "organization_id",
        "type",
        "status",
        "payload",
        "attempts",
        "max_attempts",
        "available_at",
        "locked_at",
        "locked_by",
        "last_error",
    }
    missing = expected.difference(Job.__table__.columns.keys())
    if missing:
        names = ", ".join(sorted(missing))
        raise RuntimeError(f"modelo growthos.models.Job incompatível; faltam colunas: {names}")


def _touch_heartbeat(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def build_service(settings: WorkerSettings) -> WorkerService:
    logger = configure_logging(__import__("os").getenv("LOG_LEVEL", "INFO"))

    def connect() -> Any:
        return psycopg.connect(settings.database_url, connect_timeout=5)

    return WorkerService(
        repository=PostgresJobRepository(connect),
        handlers=default_handlers(
            logger=logger,
            mock_seed=settings.mock_seed,
            latency_ms=settings.mock_latency_ms,
        ),
        worker_id=settings.worker_id,
        batch_size=settings.batch_size,
        timeout_seconds=settings.job_timeout_seconds,
        retry_base_seconds=settings.retry_base_seconds,
        retry_max_seconds=settings.retry_max_seconds,
        logger=logger,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker do DevMark GrowthOS")
    parser.add_argument("--once", action="store_true", help="processa um lote e encerra")
    args = parser.parse_args()
    settings = WorkerSettings.from_env()
    _validate_backend_contract()
    service = build_service(settings)
    stop = threading.Event()

    def request_stop(_signum: int, _frame: Any) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    _touch_heartbeat(settings.heartbeat_file)
    while not stop.is_set():
        service.run_once()
        _touch_heartbeat(settings.heartbeat_file)
        if args.once:
            break
        stop.wait(settings.poll_interval_seconds)
