from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.dependencies import AuthContext, get_current_context, require_capability
from growthos.domain.permissions import Capability
from growthos.schemas_privacy import (
    ConsentCreate,
    ConsentRead,
    DataPurposeRead,
    PrivacyExportRead,
    PrivacyRequestCreate,
    PrivacyRequestRead,
    PrivacyResolution,
    RetentionPolicyRead,
    RetentionPolicyUpdate,
    RetentionRunCreate,
    RetentionRunRead,
)
from growthos.services import privacy

router = APIRouter(prefix="/privacy")


@router.get("/purposes", response_model=list[DataPurposeRead])
def purposes(
    context: AuthContext = Depends(get_current_context), session: Session = Depends(get_session)
) -> list[DataPurposeRead]:
    return privacy.list_purposes(session, context)


@router.get("/consents", response_model=list[ConsentRead])
def consents(
    context: AuthContext = Depends(get_current_context), session: Session = Depends(get_session)
) -> list[ConsentRead]:
    return privacy.list_consents(session, context)


@router.post("/consents", response_model=ConsentRead, status_code=201)
def accept_consent(
    payload: ConsentCreate,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> ConsentRead:
    return privacy.record_consent(session, context, payload)


@router.get("/export", response_model=PrivacyExportRead)
def export(
    context: AuthContext = Depends(get_current_context), session: Session = Depends(get_session)
) -> PrivacyExportRead:
    return privacy.export_subject(session, context)


@router.get("/requests", response_model=list[PrivacyRequestRead])
def requests(
    context: AuthContext = Depends(get_current_context), session: Session = Depends(get_session)
) -> list[PrivacyRequestRead]:
    return privacy.list_requests(session, context, administrative=False)


@router.post("/requests", response_model=PrivacyRequestRead, status_code=201)
def request_privacy_action(
    payload: PrivacyRequestCreate,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> PrivacyRequestRead:
    return privacy.create_request(session, context, payload)


@router.get("/admin/requests", response_model=list[PrivacyRequestRead])
def administrative_requests(
    context: AuthContext = Depends(get_current_context), session: Session = Depends(get_session)
) -> list[PrivacyRequestRead]:
    require_capability(context, Capability.ORGANIZATION_MANAGE)
    return privacy.list_requests(session, context, administrative=True)


@router.post("/admin/requests/{request_id}/resolve", response_model=PrivacyRequestRead)
def resolve(
    request_id: UUID,
    payload: PrivacyResolution,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> PrivacyRequestRead:
    require_capability(context, Capability.ORGANIZATION_MANAGE)
    return privacy.resolve_request(session, context, request_id, payload)


@router.get("/admin/retention", response_model=list[RetentionPolicyRead])
def retention(
    context: AuthContext = Depends(get_current_context), session: Session = Depends(get_session)
) -> list[RetentionPolicyRead]:
    require_capability(context, Capability.ORGANIZATION_MANAGE)
    return privacy.list_retention(session, context)


@router.put("/admin/retention/{resource_type}", response_model=RetentionPolicyRead)
def update_retention(
    resource_type: str,
    payload: RetentionPolicyUpdate,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> RetentionPolicyRead:
    require_capability(context, Capability.ORGANIZATION_MANAGE)
    return privacy.save_retention(session, context, resource_type, payload)


@router.post("/admin/retention/run", response_model=RetentionRunRead)
def run_retention(
    payload: RetentionRunCreate,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> RetentionRunRead:
    require_capability(context, Capability.ORGANIZATION_MANAGE)
    return privacy.run_retention(session, context, payload)
