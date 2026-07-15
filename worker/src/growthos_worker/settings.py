from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} precisa ser um número inteiro") from exc
    if value <= 0:
        raise ValueError(f"{name} precisa ser maior que zero")
    return value


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise ValueError("DATABASE_URL é obrigatória para o worker")
    # SQLAlchemy usa esse prefixo; psycopg recebe a URI PostgreSQL padrão.
    return value.replace("postgresql+psycopg://", "postgresql://", 1)


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    database_url: str
    worker_id: str
    poll_interval_seconds: int
    batch_size: int
    job_timeout_seconds: int
    retry_base_seconds: int
    retry_max_seconds: int
    heartbeat_file: Path
    heartbeat_max_age_seconds: int
    mock_seed: str
    mock_latency_ms: int

    @classmethod
    def from_env(cls) -> WorkerSettings:
        default_worker_id = f"{socket.gethostname()}-{os.getpid()}"
        worker_id = os.getenv("WORKER_ID", default_worker_id).strip()
        if not worker_id:
            raise ValueError("WORKER_ID não pode ser vazio")
        return cls(
            database_url=_database_url(),
            worker_id=worker_id[:120],
            poll_interval_seconds=_positive_int("JOB_POLL_INTERVAL_SECONDS", 2),
            batch_size=_positive_int("JOB_BATCH_SIZE", 10),
            job_timeout_seconds=_positive_int("JOB_TIMEOUT_SECONDS", 120),
            retry_base_seconds=_positive_int("JOB_RETRY_BASE_SECONDS", 5),
            retry_max_seconds=_positive_int("JOB_RETRY_MAX_SECONDS", 300),
            heartbeat_file=Path(
                os.getenv("WORKER_HEARTBEAT_FILE", "/tmp/growthos-worker-heartbeat")
            ),
            heartbeat_max_age_seconds=_positive_int("WORKER_HEARTBEAT_MAX_AGE_SECONDS", 30),
            mock_seed=os.getenv("MOCK_PROVIDER_SEED", "devmark-growthos"),
            mock_latency_ms=max(0, int(os.getenv("MOCK_PROVIDER_LATENCY_MS", "0"))),
        )
