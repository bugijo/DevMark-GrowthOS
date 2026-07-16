from __future__ import annotations

import os
import socket
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


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


def _required_secret(name: str, fallback_name: str | None = None) -> str:
    value = os.getenv(name, "").strip()
    if not value and fallback_name is not None:
        value = os.getenv(fallback_name, "").strip()
    if len(value.encode("utf-8")) < 32:
        fallback = f" ou {fallback_name}" if fallback_name else ""
        raise ValueError(f"{name}{fallback} precisa ter ao menos 32 bytes")
    return value


def _frontend_url() -> str:
    value = os.getenv("FRONTEND_URL", "http://localhost:3000").strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("FRONTEND_URL precisa ser uma URL HTTP(S) absoluta")
    return value


def _email_provider() -> str:
    value = os.getenv("EMAIL_PROVIDER", "console").strip().casefold()
    if value not in {"console", "smtp"}:
        raise ValueError("EMAIL_PROVIDER precisa ser console ou smtp")
    return value


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
    email_provider: str
    smtp_host: str
    smtp_port: int
    smtp_from: str
    frontend_url: str
    token_secret_key: str = field(repr=False)

    @classmethod
    def from_env(cls) -> WorkerSettings:
        default_worker_id = f"{socket.gethostname()}-{os.getpid()}"
        worker_id = os.getenv("WORKER_ID", default_worker_id).strip()
        if not worker_id:
            raise ValueError("WORKER_ID não pode ser vazio")
        email_provider = _email_provider()
        smtp_host = os.getenv("SMTP_HOST", "").strip()
        if email_provider == "smtp" and not smtp_host:
            raise ValueError("SMTP_HOST é obrigatório quando EMAIL_PROVIDER=smtp")
        smtp_from = os.getenv(
            "SMTP_FROM",
            os.getenv("EMAIL_FROM", "no-reply@devmark.local"),
        ).strip()
        if "@" not in smtp_from or any(character in smtp_from for character in "\r\n"):
            raise ValueError("SMTP_FROM precisa ser um endereço de e-mail seguro")
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
            email_provider=email_provider,
            smtp_host=smtp_host,
            smtp_port=_positive_int("SMTP_PORT", 1025),
            smtp_from=smtp_from,
            frontend_url=_frontend_url(),
            token_secret_key=_required_secret("TOKEN_SECRET_KEY", "AUTH_SECRET_KEY"),
        )

    @property
    def effective_token_secret_key(self) -> str:
        """Chave efetiva, já resolvida de TOKEN_SECRET_KEY ou AUTH_SECRET_KEY."""

        return self.token_secret_key
