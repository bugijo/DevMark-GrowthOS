from pathlib import Path

import pytest

from growthos_worker.settings import WorkerSettings


def set_minimum_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:password@postgres/db")
    monkeypatch.setenv("AUTH_SECRET_KEY", "auth-secret-with-at-least-thirty-two-characters")
    monkeypatch.setenv("WORKER_HEARTBEAT_FILE", "/tmp/test-growthos-heartbeat")


def test_settings_use_auth_secret_as_token_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    set_minimum_environment(monkeypatch)
    monkeypatch.delenv("TOKEN_SECRET_KEY", raising=False)
    monkeypatch.setenv("EMAIL_PROVIDER", "console")

    settings = WorkerSettings.from_env()

    assert settings.email_provider == "console"
    assert settings.smtp_port == 1025
    assert settings.smtp_from == "no-reply@devmark.local"
    assert settings.frontend_url == "http://localhost:3000"
    assert settings.effective_token_secret_key == (
        "auth-secret-with-at-least-thirty-two-characters"
    )
    assert settings.heartbeat_file == Path("/tmp/test-growthos-heartbeat")
    assert "auth-secret" not in repr(settings)


def test_settings_prefer_dedicated_token_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    set_minimum_environment(monkeypatch)
    monkeypatch.setenv("TOKEN_SECRET_KEY", "dedicated-token-secret-with-at-least-thirty-two-bytes")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "mailpit")
    monkeypatch.setenv("SMTP_PORT", "1025")
    monkeypatch.setenv("SMTP_FROM", "growthos@devmark.local")
    monkeypatch.setenv("FRONTEND_URL", "http://frontend:3000/")

    settings = WorkerSettings.from_env()

    assert settings.smtp_host == "mailpit"
    assert settings.smtp_from == "growthos@devmark.local"
    assert settings.frontend_url == "http://frontend:3000"
    assert settings.effective_token_secret_key.startswith("dedicated-token-secret")


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("EMAIL_PROVIDER", "external", "console ou smtp"),
        ("FRONTEND_URL", "javascript:alert(1)", "HTTP\\(S\\) absoluta"),
        ("AUTH_SECRET_KEY", "short", "ao menos 32 bytes"),
    ],
)
def test_settings_reject_unsafe_email_and_token_configuration(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
    message: str,
) -> None:
    set_minimum_environment(monkeypatch)
    monkeypatch.delenv("TOKEN_SECRET_KEY", raising=False)
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError, match=message):
        WorkerSettings.from_env()


def test_smtp_provider_requires_host(monkeypatch: pytest.MonkeyPatch) -> None:
    set_minimum_environment(monkeypatch)
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "")

    with pytest.raises(ValueError, match="SMTP_HOST"):
        WorkerSettings.from_env()
