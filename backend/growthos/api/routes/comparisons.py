from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.dependencies import AuthContext, get_current_context, require_capability
from growthos.domain.permissions import Capability
from growthos.schemas_comparisons import (
    ContentVersionComparisonRead,
    ContentVersionHistoryRead,
    StrategyVersionComparisonRead,
    StrategyVersionHistoryRead,
)
from growthos.services import comparisons

router = APIRouter()


@router.get(
    "/contents/{content_id}/history",
    response_model=ContentVersionHistoryRead,
)
def content_version_history(
    content_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> ContentVersionHistoryRead:
    require_capability(context, Capability.CONTENT_VIEW)
    return comparisons.content_history(session, context, content_id)


@router.get(
    "/contents/{content_id}/compare",
    response_model=ContentVersionComparisonRead,
)
def compare_content_versions(
    content_id: UUID,
    base_version_id: UUID = Query(),
    target_version_id: UUID = Query(),
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> ContentVersionComparisonRead:
    require_capability(context, Capability.CONTENT_VIEW)
    return comparisons.compare_content_versions(
        session,
        context,
        content_id,
        base_version_id,
        target_version_id,
    )


@router.get(
    "/strategies/{strategy_id}/history",
    response_model=StrategyVersionHistoryRead,
)
def strategy_version_history(
    strategy_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> StrategyVersionHistoryRead:
    require_capability(context, Capability.STRATEGY_VIEW)
    return comparisons.strategy_history(session, context, strategy_id)


@router.get(
    "/strategies/{strategy_id}/compare",
    response_model=StrategyVersionComparisonRead,
)
def compare_strategy_versions(
    strategy_id: UUID,
    base_version_id: UUID = Query(),
    target_version_id: UUID = Query(),
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> StrategyVersionComparisonRead:
    require_capability(context, Capability.STRATEGY_VIEW)
    return comparisons.compare_strategy_versions(
        session,
        context,
        strategy_id,
        base_version_id,
        target_version_id,
    )
