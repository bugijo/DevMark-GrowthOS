from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from growthos.config import Settings, get_settings
from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    require_capability,
    require_csrf,
)
from growthos.domain.enums import ApprovalComponent
from growthos.domain.permissions import Capability
from growthos.schemas import (
    ChangesRequest,
    ContentGenerateRequest,
    ContentRead,
    ContentRevisionCreate,
    ContentVisualRevisionCreate,
    DecisionRequest,
    ManualPublicationCreate,
)
from growthos.services.content import approvals as content_approvals
from growthos.services.content import generation as content_generation
from growthos.services.content import publication as content_publication
from growthos.services.content import read_models as content_reads
from growthos.services.content import revisions as content_revisions

router = APIRouter()


@router.post("/generate", response_model=ContentRead, status_code=status.HTTP_201_CREATED)
def generate_content(
    payload: ContentGenerateRequest,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_CREATE)
    if settings.ai_provider != "mock":
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Somente o provider mock está habilitado nesta versão",
        )
    return content_generation.generate_content(session, context, payload)


@router.get("", response_model=list[ContentRead])
def list_contents(
    business_id: UUID | None = Query(default=None),
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[ContentRead]:
    require_capability(context, Capability.CONTENT_VIEW)
    return content_reads.list_contents(session, context, business_id)


@router.get("/{content_id}", response_model=ContentRead)
def get_content(
    content_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_VIEW)
    content = content_reads.get_content(session, context, content_id)
    return content_reads.serialize_content(session, content, context)


@router.post("/{content_id}/submit-internal", response_model=ContentRead)
def submit_internal(
    content_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_SUBMIT_INTERNAL)
    return content_approvals.submit_internal(session, context, content_id)


@router.post("/{content_id}/send-to-client", response_model=ContentRead)
def send_to_client(
    content_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_SEND_CLIENT)
    return content_approvals.send_to_client(session, context, content_id)


@router.post("/{content_id}/approve", response_model=ContentRead)
def approve_content(
    content_id: UUID,
    payload: DecisionRequest | None = None,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_DECIDE_CLIENT)
    return content_approvals.approve_content(session, context, content_id, payload)


@router.post(
    "/{content_id}/decisions/{component}/approve",
    response_model=ContentRead,
)
def approve_content_component(
    content_id: UUID,
    component: ApprovalComponent,
    payload: DecisionRequest | None = None,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_DECIDE_CLIENT)
    return content_approvals.approve_content_component(
        session,
        context,
        content_id,
        component,
        payload,
    )


@router.post("/{content_id}/request-changes", response_model=ContentRead)
def request_changes(
    content_id: UUID,
    payload: ChangesRequest,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_DECIDE_CLIENT)
    return content_approvals.request_component_changes(
        session,
        context,
        content_id,
        ApprovalComponent.TEXT,
        payload.comment.strip(),
    )


@router.post(
    "/{content_id}/decisions/{component}/request-changes",
    response_model=ContentRead,
)
def request_content_component_changes(
    content_id: UUID,
    component: ApprovalComponent,
    payload: ChangesRequest,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_DECIDE_CLIENT)
    return content_approvals.request_component_changes(
        session,
        context,
        content_id,
        component,
        payload.comment.strip(),
    )


@router.post("/{content_id}/revisions", response_model=ContentRead)
def create_revision(
    content_id: UUID,
    payload: ContentRevisionCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_EDIT_TEXT)
    return content_revisions.create_revision(session, context, content_id, payload)


@router.post("/{content_id}/visual-revisions", response_model=ContentRead)
def create_visual_revision(
    content_id: UUID,
    payload: ContentVisualRevisionCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.CONTENT_EDIT_VISUAL)
    return content_revisions.create_visual_revision(session, context, content_id, payload)


@router.post("/{content_id}/publication", response_model=ContentRead)
def record_manual_publication(
    content_id: UUID,
    payload: ManualPublicationCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentRead:
    require_capability(context, Capability.PUBLICATION_RECORD)
    return content_publication.record_manual_publication(session, context, content_id, payload)
