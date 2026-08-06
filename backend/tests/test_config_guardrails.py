import pytest

from growthos.config import Settings, UnsafeConfigurationError
from growthos.database import get_session_factory
from growthos.seed import seed_demo

SAFE_PRODUCTION_SECRET = "g8B!2zQ#9mK$4vN@7xR%3cT&6pL*1sD_5wF+0hJ"


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "production",
        "auth_secret_key": SAFE_PRODUCTION_SECRET,
        "session_cookie_secure": True,
        "ai_provider": "mock",
        "seed_demo_data": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_secure_production_configuration_accepts_mock_provider() -> None:
    settings = production_settings()

    assert settings.app_env == "production"
    assert settings.ai_provider == "mock"
    assert settings.session_cookie_secure is True


def test_test_environment_ignores_external_ai_credentials() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        auth_secret_key=SAFE_PRODUCTION_SECRET,
        ai_external_enabled=True,
        openrouter_api_key="must-not-be-used",
        hermes_base_url="http://127.0.0.1:11434",
    )

    assert settings.external_ai_allowed is False
    assert settings.ai_external_enabled is False
    assert settings.openrouter_api_key is None
    assert settings.hermes_base_url == ""


def test_production_rejects_wildcard_cors_origin() -> None:
    with pytest.raises(UnsafeConfigurationError, match="ALLOWED_ORIGINS"):
        production_settings(allowed_origins="*")


def test_cookie_same_site_accepts_only_supported_values() -> None:
    with pytest.raises(ValueError, match="SESSION_COOKIE_SAME_SITE"):
        Settings(
            _env_file=None,
            auth_secret_key=SAFE_PRODUCTION_SECRET,
            session_cookie_same_site="invalid",
        )


def test_antimalware_provider_accepts_only_local_mock_or_disabled() -> None:
    with pytest.raises(ValueError, match="ANTIMALWARE_PROVIDER"):
        Settings(
            _env_file=None,
            auth_secret_key=SAFE_PRODUCTION_SECRET,
            antimalware_provider="unknown",
        )


@pytest.mark.parametrize(
    "secret",
    [
        "development-only-secret-key-change-me-1234567890",
        "local-auth-key-change-before-shared-use-at-least-32-characters",
        "demo-secret-value-with-more-than-thirty-two-characters",
    ],
)
def test_production_rejects_local_default_or_demo_auth_secret(secret: str) -> None:
    with pytest.raises(UnsafeConfigurationError) as error:
        production_settings(auth_secret_key=secret)

    assert "AUTH_SECRET_KEY" in str(error.value)
    assert secret not in str(error.value)


def test_auth_secret_minimum_length_is_enforced_without_echoing_value() -> None:
    secret = "short-secret"

    with pytest.raises(UnsafeConfigurationError) as error:
        Settings(_env_file=None, auth_secret_key=secret)

    assert "32 caracteres" in str(error.value)
    assert secret not in str(error.value)


@pytest.mark.parametrize(
    ("overrides", "expected_variable"),
    [
        ({"session_cookie_secure": False}, "SESSION_COOKIE_SECURE"),
        ({"ai_provider": "external"}, "AI_PROVIDER"),
        ({"antimalware_provider": "disabled"}, "ANTIMALWARE_PROVIDER"),
        ({"antimalware_fail_closed": False}, "ANTIMALWARE_FAIL_CLOSED"),
        ({"seed_demo_data": True}, "SEED_DEMO_DATA"),
    ],
)
def test_production_rejects_unsupported_or_unsafe_modes(
    overrides: dict[str, object], expected_variable: str
) -> None:
    with pytest.raises(UnsafeConfigurationError) as error:
        production_settings(**overrides)

    assert expected_variable in str(error.value)


def test_enabled_demo_seed_requires_distinct_credentials() -> None:
    with pytest.raises(UnsafeConfigurationError, match="devem ser diferentes"):
        Settings(
            _env_file=None,
            app_env="development",
            auth_secret_key=SAFE_PRODUCTION_SECRET,
            seed_demo_data=True,
            demo_admin_password="same-demo-password",
            demo_client_password="same-demo-password",
        )


def test_direct_demo_seed_command_is_blocked_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = production_settings()

    def get_production_settings() -> Settings:
        return settings

    monkeypatch.setattr("growthos.seed.get_settings", get_production_settings)

    with (
        get_session_factory()() as session,
        pytest.raises(UnsafeConfigurationError, match="não pode executar em produção"),
    ):
        seed_demo(session)
