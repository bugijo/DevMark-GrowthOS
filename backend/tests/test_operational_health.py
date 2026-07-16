from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

from growthos.api.routes.health import _readiness
from growthos.config import Settings
from growthos.security_headers import security_headers_for


def test_liveness_readiness_and_legacy_health_are_available(client: Any) -> None:
    assert client.get("/api/v1/health/live").json() == {"status": "ok"}
    ready = client.get("/api/v1/health/ready")
    legacy = client.get("/api/v1/health")

    assert ready.status_code == 200
    assert ready.json() == legacy.json()
    assert ready.headers["Cache-Control"] == "no-store"
    assert ready.headers["X-Content-Type-Options"] == "nosniff"
    assert "Strict-Transport-Security" not in ready.headers


def test_readiness_fails_safely_when_database_is_unavailable() -> None:
    class UnavailableSession:
        def execute(self, _statement: object) -> None:
            raise OperationalError("SELECT 1", {}, RuntimeError("private database detail"))

    settings = Settings(
        _env_file=None,
        auth_secret_key="test-auth-secret-with-at-least-thirty-two-characters",
    )
    with pytest.raises(HTTPException) as error:
        _readiness(UnavailableSession(), settings)  # type: ignore[arg-type]

    assert error.value.status_code == 503
    assert "private database detail" not in str(error.value.detail)


def test_hsts_and_api_csp_are_enabled_only_in_production() -> None:
    development = security_headers_for("development", api_response=True)
    production = security_headers_for("production", api_response=True)

    assert "Strict-Transport-Security" not in development
    assert "Content-Security-Policy" not in development
    assert production["Strict-Transport-Security"].startswith("max-age=")
    assert "frame-ancestors 'none'" in production["Content-Security-Policy"]
