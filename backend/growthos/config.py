from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    auth_secret_key: str = Field(
        default="development-only-secret-key-change-me-1234567890",
        min_length=32,
    )
    access_token_ttl_minutes: int = 30
    session_cookie_name: str = "growthos_session"
    csrf_cookie_name: str = "growthos_csrf"
    session_cookie_secure: bool = False
    session_cookie_same_site: str = "lax"
    allowed_origins: str = "http://localhost:3000"
    ai_provider: str = "mock"
    mock_provider_seed: str = "devmark-growthos"
    demo_organization_name: str = "DevMark Demo"
    demo_admin_email: str = "admin@devmark.local"
    demo_admin_password: str = "local-demo-only-change-before-use"
    demo_client_email: str = "client@clinicafeliz.local"
    demo_client_password: str = "local-demo-client-only-change-before-use"

    @property
    def cors_origins(self) -> list[str]:
        return [value.strip() for value in self.allowed_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
