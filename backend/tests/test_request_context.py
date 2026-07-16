import json
import logging
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from growthos.client_ip import resolve_client_ip
from growthos.config import Settings
from growthos.logging_config import JsonFormatter


def test_request_id_is_echoed_and_invalid_value_is_replaced(client: TestClient) -> None:
    valid = "pilot-request-123"
    accepted = client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": valid},
    )
    assert accepted.headers["X-Request-ID"] == valid

    rejected = client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": "x" * 100},
    )
    assert rejected.headers["X-Request-ID"] != "x" * 100
    UUID(rejected.headers["X-Request-ID"])


def test_forwarded_origin_is_ignored_without_a_trusted_proxy() -> None:
    assert (
        resolve_client_ip(
            "203.0.113.10",
            "198.51.100.20",
            trusted_proxy_cidrs="10.0.0.0/8",
        )
        == "203.0.113.10"
    )


def test_forwarded_chain_uses_the_nearest_untrusted_address() -> None:
    assert (
        resolve_client_ip(
            "10.0.0.8",
            "198.51.100.20, 10.0.0.7",
            trusted_proxy_cidrs="10.0.0.0/8",
        )
        == "198.51.100.20"
    )


@pytest.mark.parametrize(
    "header",
    ["not-an-ip", "198.51.100.20,", ",198.51.100.20"],
)
def test_malformed_forwarded_chain_falls_back_to_the_peer(header: str) -> None:
    assert (
        resolve_client_ip(
            "10.0.0.8",
            header,
            trusted_proxy_cidrs="10.0.0.0/8",
        )
        == "10.0.0.8"
    )


def test_invalid_trusted_proxy_network_is_rejected() -> None:
    with pytest.raises(ValueError, match="TRUSTED_PROXY_CIDRS"):
        Settings(
            _env_file=None,
            auth_secret_key="test-auth-secret-with-at-least-thirty-two-characters",
            trusted_proxy_cidrs="invalid-network",
        )


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValueError, match="LOG_LEVEL"):
        Settings(
            _env_file=None,
            auth_secret_key="test-auth-secret-with-at-least-thirty-two-characters",
            log_level="verbose",
        )


def test_backend_json_log_contains_only_explicit_context() -> None:
    record = logging.LogRecord(
        name="growthos.backend",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="http request completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-123"
    record.path = "/api/v1/health/live"
    record.status_code = 200

    payload = json.loads(JsonFormatter().format(record))

    assert payload["service"] == "backend"
    assert payload["request_id"] == "request-123"
    assert payload["path"] == "/api/v1/health/live"
    assert "cookie" not in payload
    assert "authorization" not in payload
