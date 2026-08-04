from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.dependencies import AuthContext, get_current_context, require_capability
from growthos.domain.permissions import Capability
from growthos.schemas_providers import ProviderConfigRead, ProviderConfigUpdate, ProviderTestRead
from growthos.services.provider_configs import (
    list_provider_configs,
    test_provider,
    update_provider_config,
)

router = APIRouter(prefix="/providers")


@router.get("", response_model=list[ProviderConfigRead])
def list_configs(
    context: AuthContext = Depends(get_current_context), session: Session = Depends(get_session)
) -> list[ProviderConfigRead]:
    require_capability(context, Capability.PROVIDER_CONFIG_VIEW)
    return list_provider_configs(session, context)


@router.put("/{kind}/{provider}", response_model=ProviderConfigRead)
def update_config(
    kind: str,
    provider: str,
    payload: ProviderConfigUpdate,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> ProviderConfigRead:
    require_capability(context, Capability.PROVIDER_CONFIG_MANAGE)
    return update_provider_config(session, context, kind.upper(), provider.upper(), payload)


@router.post("/{kind}/{provider}/test", response_model=ProviderTestRead)
def test_connection(
    kind: str,
    provider: str,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> ProviderTestRead:
    require_capability(context, Capability.PROVIDER_CONFIG_MANAGE)
    return test_provider(session, context, kind.upper(), provider.upper())
