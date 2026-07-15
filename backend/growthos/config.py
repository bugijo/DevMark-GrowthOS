from functools import lru_cache
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class UnsafeConfigurationError(RuntimeError):
    """Raised without echoing secret values when runtime configuration is unsafe."""


_INSECURE_PRODUCTION_SECRET_MARKERS = (
    "change-me",
    "change-before",
    "default",
    "demo",
    "development-only",
    "example",
    "local-auth",
    "tests-only",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "DevMark GrowthOS"
    app_env: str = "development"
    app_version: str = "0.1.0-dev"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite+pysqlite:///./growthos.db"
    auth_secret_key: str = "development-only-secret-key-change-me-1234567890"
    access_token_ttl_minutes: int = 30
    login_rate_limit_attempts: int = Field(default=10, ge=1)
    login_rate_limit_window_seconds: int = Field(default=60, ge=1)
    session_cookie_name: str = "growthos_session"
    csrf_cookie_name: str = "growthos_csrf"
    session_cookie_secure: bool = False
    session_cookie_same_site: str = "lax"
    allowed_origins: str = "http://localhost:3000"
    ai_provider: str = "mock"
    mock_provider_seed: str = "devmark-growthos"
    seed_demo_data: bool = False
    demo_organization_name: str = "DevMark Demo"
    demo_admin_email: str = "admin@devmark.local"
    demo_admin_password: str = "local-demo-only-change-before-use"
    demo_client_email: str = "client@clinicafeliz.local"
    demo_client_password: str = "local-demo-client-only-change-before-use"

    @field_validator("app_env", "ai_provider", mode="before")
    @classmethod
    def normalize_mode(cls, value: object) -> object:
        return value.strip().casefold() if isinstance(value, str) else value

    @model_validator(mode="after")
    def reject_unsafe_runtime_configuration(self) -> Self:
        problems: list[str] = []
        if len(self.auth_secret_key) < 32:
            problems.append("AUTH_SECRET_KEY deve ter ao menos 32 caracteres")

        if self.app_env == "production":
            normalized_secret = self.auth_secret_key.casefold()
            if any(marker in normalized_secret for marker in _INSECURE_PRODUCTION_SECRET_MARKERS):
                problems.append("AUTH_SECRET_KEY não pode usar valor local, demo ou padrão")
            if not self.session_cookie_secure:
                problems.append("SESSION_COOKIE_SECURE deve ser true")
            if self.ai_provider != "mock":
                problems.append("AI_PROVIDER deve ser mock nesta versão")
            if self.seed_demo_data:
                problems.append("SEED_DEMO_DATA deve ser false")

        if self.seed_demo_data:
            problems.extend(self._demo_credentials_problems())

        if problems:
            raise UnsafeConfigurationError("Configuração insegura: " + "; ".join(problems))
        return self

    def ensure_demo_seed_allowed(self) -> None:
        problems = self._demo_credentials_problems()
        if self.app_env == "production":
            problems.insert(0, "seed de demonstração não pode executar em produção")
        if problems:
            raise UnsafeConfigurationError("Seed de demonstração bloqueado: " + "; ".join(problems))

    def _demo_credentials_problems(self) -> list[str]:
        problems: list[str] = []
        if len(self.demo_admin_password) < 12:
            problems.append("DEMO_ADMIN_PASSWORD deve ter ao menos 12 caracteres")
        if len(self.demo_client_password) < 12:
            problems.append("DEMO_CLIENT_PASSWORD deve ter ao menos 12 caracteres")
        if self.demo_admin_password == self.demo_client_password:
            problems.append("as senhas demo de agência e cliente devem ser diferentes")
        if self.demo_admin_email.strip().casefold() == self.demo_client_email.strip().casefold():
            problems.append("os e-mails demo de agência e cliente devem ser diferentes")
        return problems

    @property
    def cors_origins(self) -> list[str]:
        return [value.strip() for value in self.allowed_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
