import os
from datetime import UTC, datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext
from growthos.models.provider_config import ProviderConfig
from growthos.schemas_providers import ProviderConfigRead, ProviderConfigUpdate, ProviderTestRead
from growthos.services.audit import add_audit_log

_CATALOG = (
    ("TEXT", "MOCK", True),
    ("TEXT", "HERMES", False),
    ("TEXT", "EXTERNAL_FUTURE", False),
    ("IMAGE", "MOCK", True),
    ("IMAGE", "EXTERNAL_FUTURE", False),
    ("EMAIL", "MOCK", True),
    ("EMAIL", "SMTP", False),
    ("STORAGE", "MINIO", True),
    ("ORCHESTRATION", "MOCK", True),
    ("ORCHESTRATION", "HERMES", False),
)


def _environment_available(provider: str, secret_key: str | None) -> bool:
    if provider == "HERMES":
        return bool(os.getenv("HERMES_BASE_URL"))
    if provider == "EXTERNAL_FUTURE":
        return bool(secret_key and os.getenv(secret_key))
    return True


def _read(
    kind: str, provider: str, required: bool, row: ProviderConfig | None
) -> ProviderConfigRead:
    secret_key = row.secret_environment_key if row else None
    return ProviderConfigRead(
        id=row.id if row else None,
        kind=kind,
        provider=provider,
        is_active=row.is_active if row else required,
        is_required=required,
        configured_by_environment=_environment_available(provider, secret_key),
        priority=row.priority if row else (0 if required else 100),
        fallback_provider=row.fallback_provider if row else (None if required else "MOCK"),
        timeout_seconds=row.timeout_seconds if row else 10,
        max_attempts=row.max_attempts if row else 1,
        test_mode=row.test_mode if row else True,
        secret_environment_key=secret_key,
        last_checked_at=row.last_checked_at if row else None,
        last_status=row.last_status if row else "READY" if required else "NOT_CHECKED",
        last_error=row.last_error if row else None,
    )


def list_provider_configs(session: Session, context: AuthContext) -> list[ProviderConfigRead]:
    rows = session.scalars(
        select(ProviderConfig).where(ProviderConfig.organization_id == context.organization.id)
    ).all()
    by_key = {(row.kind, row.provider): row for row in rows}
    return [
        _read(kind, provider, required, by_key.get((kind, provider)))
        for kind, provider, required in _CATALOG
    ]


def update_provider_config(
    session: Session, context: AuthContext, kind: str, provider: str, data: ProviderConfigUpdate
) -> ProviderConfigRead:
    catalog = {
        (item_kind, item_provider): required for item_kind, item_provider, required in _CATALOG
    }
    required = catalog.get((kind, provider))
    if required is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider não encontrado")
    if required and not data.is_active:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "O provider obrigatório não pode ser desativado"
        )
    if provider != "MOCK" and data.fallback_provider != "MOCK":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Providers opcionais exigem fallback explícito para MOCK",
        )
    if provider in {"MOCK", "MINIO", "SMTP", "HERMES"} and data.secret_environment_key:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Este provider usa somente variáveis de ambiente próprias",
        )
    row = session.scalar(
        select(ProviderConfig).where(
            ProviderConfig.organization_id == context.organization.id,
            ProviderConfig.kind == kind,
            ProviderConfig.provider == provider,
        )
    )
    if row is None:
        row = ProviderConfig(organization_id=context.organization.id, kind=kind, provider=provider)
        session.add(row)
    for field, value in data.model_dump().items():
        setattr(row, field, value)
    row.updated_by_user_id = context.user.id
    session.flush()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        actor_user_id=context.user.id,
        action="provider.config_updated",
        resource_type="provider_config",
        resource_id=row.id,
        details={"kind": kind, "provider": provider, "active": row.is_active},
    )
    session.commit()
    session.refresh(row)
    return _read(kind, provider, required, row)


def _probe(provider: str, timeout: int) -> tuple[str, str]:
    if provider == "MOCK":
        return "HEALTHY", "Provider mock determinístico disponível."
    if provider == "MINIO":
        return (
            "HEALTHY",
            "Storage configurado pelo ambiente; valide dependências no healthcheck operacional.",
        )
    if provider == "SMTP":
        return "HEALTHY", "SMTP configurado pelo ambiente; nenhuma mensagem foi enviada no teste."
    if provider == "EXTERNAL_FUTURE":
        return "DISABLED", "Provider futuro estrutural; conexão externa desabilitada na versão 1.0."
    base_url = os.getenv("HERMES_BASE_URL", "").rstrip("/")
    if not base_url:
        return "DISABLED", "Hermes opcional não está configurado; o fallback mock permanece ativo."
    try:
        with urlopen(Request(f"{base_url}/health", method="GET"), timeout=timeout) as response:
            if 200 <= response.status < 300:
                return "HEALTHY", "Hermes respondeu ao healthcheck."
    except (OSError, URLError, TimeoutError):
        return "UNAVAILABLE", "Hermes não respondeu; o fallback mock permanece ativo."
    return "UNAVAILABLE", "Hermes retornou estado indisponível; o fallback mock permanece ativo."


def test_provider(
    session: Session, context: AuthContext, kind: str, provider: str
) -> ProviderTestRead:
    catalog = {
        (item_kind, item_provider): required for item_kind, item_provider, required in _CATALOG
    }
    required = catalog.get((kind, provider))
    if required is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider não encontrado")
    row = session.scalar(
        select(ProviderConfig).where(
            ProviderConfig.organization_id == context.organization.id,
            ProviderConfig.kind == kind,
            ProviderConfig.provider == provider,
        )
    )
    timeout = row.timeout_seconds if row else 10
    checked_at = datetime.now(UTC)
    checked_status, message = _probe(provider, timeout)
    if row is not None:
        row.last_checked_at = checked_at
        row.last_status = checked_status
        row.last_error = message if checked_status == "UNAVAILABLE" else None
        add_audit_log(
            session,
            organization_id=context.organization.id,
            actor_user_id=context.user.id,
            action="provider.connection_tested",
            resource_type="provider_config",
            resource_id=row.id,
            details={"kind": kind, "provider": provider, "status": checked_status},
        )
        session.commit()
    return ProviderTestRead(
        kind=kind, provider=provider, status=checked_status, checked_at=checked_at, message=message
    )
