from functools import lru_cache
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from growthos.client_ip import parse_trusted_proxy_cidrs


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
    token_secret_key: str | None = None
    access_token_ttl_minutes: int = 30
    invitation_ttl_hours: int = Field(default=72, ge=1, le=720)
    password_reset_ttl_minutes: int = Field(default=30, ge=5, le=1440)
    security_rate_limit_attempts: int = Field(default=5, ge=1)
    security_rate_limit_window_seconds: int = Field(default=300, ge=1)
    frontend_url: str = "http://localhost:3000"
    login_rate_limit_attempts: int = Field(default=10, ge=1)
    login_rate_limit_window_seconds: int = Field(default=60, ge=1)
    login_rate_limit_origin_multiplier: int = Field(default=20, ge=1)
    session_cookie_name: str = "growthos_session"
    csrf_cookie_name: str = "growthos_csrf"
    session_cookie_secure: bool = False
    session_cookie_same_site: str = "lax"
    allowed_origins: str = "http://localhost:3000"
    trusted_proxy_cidrs: str = ""
    log_level: str = "INFO"
    ai_provider: str = "mock"
    mock_provider_seed: str = "devmark-growthos"
    storage_provider: str = "minio"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_public_endpoint_url: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "growthos-local"
    s3_access_key_id: str = "growthos_minio_local"
    s3_secret_access_key: str = "local-minio-only-change-before-shared-use"
    s3_use_ssl: bool = False
    max_upload_size_mb: int = Field(default=10, ge=1, le=50)
    allowed_upload_mime_types: str = "image/jpeg,image/png,image/webp"
    signed_url_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    seed_demo_data: bool = False
    demo_organization_name: str = "DevMark Demo"
    demo_admin_email: str = "admin@devmark.local"
    demo_admin_password: str = "local-demo-only-change-before-use"
    demo_client_email: str = "client@clinicafeliz.local"
    demo_client_password: str = "local-demo-client-only-change-before-use"

    antimalware_provider: str = "mock"
    antimalware_fail_closed: bool = True

    @field_validator("app_env", "ai_provider", "antimalware_provider", mode="before")
    @classmethod
    def normalize_mode(cls, value: object) -> object:
        return value.strip().casefold() if isinstance(value, str) else value

    @field_validator("antimalware_provider")
    @classmethod
    def validate_antimalware_provider(cls, value: str) -> str:
        if value not in {"mock", "disabled"}:
            raise ValueError("ANTIMALWARE_PROVIDER deve ser mock ou disabled")
        return value

    @field_validator("session_cookie_same_site", mode="before")
    @classmethod
    def validate_cookie_same_site(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip().casefold()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("SESSION_COOKIE_SAME_SITE deve ser lax, strict ou none")
        return normalized

    @field_validator("trusted_proxy_cidrs")
    @classmethod
    def validate_trusted_proxy_cidrs(cls, value: str) -> str:
        try:
            parse_trusted_proxy_cidrs(value)
        except ValueError as exc:
            raise ValueError("TRUSTED_PROXY_CIDRS contém uma rede inválida") from exc
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL deve ser DEBUG, INFO, WARNING, ERROR ou CRITICAL")
        return normalized

    @model_validator(mode="after")
    def reject_unsafe_runtime_configuration(self) -> Self:
        problems: list[str] = []
        if len(self.auth_secret_key) < 32:
            problems.append("AUTH_SECRET_KEY deve ter ao menos 32 caracteres")
        if self.token_secret_key is not None and len(self.token_secret_key) < 32:
            problems.append("TOKEN_SECRET_KEY deve ter ao menos 32 caracteres")

        if self.app_env == "production":
            normalized_secret = self.auth_secret_key.casefold()
            if any(marker in normalized_secret for marker in _INSECURE_PRODUCTION_SECRET_MARKERS):
                problems.append("AUTH_SECRET_KEY não pode usar valor local, demo ou padrão")
            if self.token_secret_key is not None:
                normalized_token_secret = self.token_secret_key.casefold()
                if any(
                    marker in normalized_token_secret
                    for marker in _INSECURE_PRODUCTION_SECRET_MARKERS
                ):
                    problems.append("TOKEN_SECRET_KEY não pode usar valor local, demo ou padrão")
            if not self.session_cookie_secure:
                problems.append("SESSION_COOKIE_SECURE deve ser true")
            if self.ai_provider != "mock":
                problems.append("AI_PROVIDER deve ser mock nesta versão")
            if self.antimalware_provider == "disabled":
                problems.append("ANTIMALWARE_PROVIDER não pode ser disabled")
            if not self.antimalware_fail_closed:
                problems.append("ANTIMALWARE_FAIL_CLOSED deve ser true")
            if self.seed_demo_data:
                problems.append("SEED_DEMO_DATA deve ser false")
            if not self.cors_origins or any("*" in origin for origin in self.cors_origins):
                problems.append("ALLOWED_ORIGINS deve listar origens explícitas")

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

    @property
    def effective_token_secret_key(self) -> str:
        return self.token_secret_key or self.auth_secret_key

    @property
    def upload_mime_types(self) -> frozenset[str]:
        return frozenset(
            value.strip().casefold()
            for value in self.allowed_upload_mime_types.split(",")
            if value.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
