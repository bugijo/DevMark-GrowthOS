from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    get_scoped_business,
    require_capability,
)
from growthos.domain.enums import ApprovalComponent, ApprovalStatus, ContentStatus
from growthos.domain.permissions import Capability
from growthos.models import Approval, CalendarEntry, ContentItem, ContentStrategy, ContentVersion
from growthos.schemas_reports import PeriodReportRead

router = APIRouter()

_UNAVAILABLE_METRICS = [
    "alcance",
    "impressoes",
    "cliques",
    "engajamento",
    "conversoes",
    "investimento_em_midia",
]


def _period_bounds(starts_on: date, ends_on: date) -> tuple[datetime, datetime]:
    if ends_on < starts_on:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "A data final deve ser igual ou posterior à data inicial",
        )
    if ends_on - starts_on > timedelta(days=366):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "O período máximo do relatório é de 367 dias",
        )
    return (
        datetime.combine(starts_on, time.min, tzinfo=UTC),
        datetime.combine(ends_on + timedelta(days=1), time.min, tzinfo=UTC),
    )


def _enum_key(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw)


@router.get(
    "/businesses/{business_id}/reports/period",
    response_model=PeriodReportRead,
)
def get_period_report(
    business_id: UUID,
    starts_on: date = Query(),
    ends_on: date = Query(),
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> PeriodReportRead:
    require_capability(context, Capability.REPORT_VIEW)
    get_scoped_business(session, context, business_id)
    period_start, period_end = _period_bounds(starts_on, ends_on)
    organization_id = context.organization.id

    # Publicação e agendamento representam melhor o período operacional. Para
    # rascunhos ainda sem agenda, a criação é usada como referência.
    content_anchor = func.coalesce(
        ContentItem.published_at,
        ContentItem.scheduled_for,
        ContentItem.created_at,
    )
    content_scope = (
        ContentItem.organization_id == organization_id,
        ContentItem.business_id == business_id,
        content_anchor >= period_start,
        content_anchor < period_end,
    )
    content_rows = session.execute(
        select(ContentItem.status, func.count(ContentItem.id))
        .where(*content_scope)
        .group_by(ContentItem.status)
    ).all()
    content_by_status = {item.value: 0 for item in ContentStatus}
    for item_status, count in content_rows:
        content_by_status[_enum_key(item_status)] = int(count)
    content_total = sum(content_by_status.values())

    version_total = int(
        session.scalar(
            select(func.count(ContentVersion.id))
            .join(ContentItem, ContentItem.id == ContentVersion.content_item_id)
            .where(*content_scope)
        )
        or 0
    )

    approval_rows = session.execute(
        select(Approval.component, Approval.status, func.count(Approval.id))
        .join(ContentItem, ContentItem.id == Approval.content_item_id)
        .where(*content_scope)
        .group_by(Approval.component, Approval.status)
    ).all()
    approvals_by_component = {
        component.value: {approval_status.value: 0 for approval_status in ApprovalStatus}
        for component in ApprovalComponent
    }
    for component, approval_status, count in approval_rows:
        approvals_by_component[_enum_key(component)][_enum_key(approval_status)] = int(count)

    publication_rows = session.execute(
        select(ContentItem.publication_channel, func.count(ContentItem.id))
        .where(
            ContentItem.organization_id == organization_id,
            ContentItem.business_id == business_id,
            ContentItem.published_at.is_not(None),
            ContentItem.published_at >= period_start,
            ContentItem.published_at < period_end,
        )
        .group_by(ContentItem.publication_channel)
    ).all()
    publications_by_channel = {
        channel or "nao_informado": int(count) for channel, count in publication_rows
    }
    manual_publications_total = sum(publications_by_channel.values())

    strategies_total = int(
        session.scalar(
            select(func.count(ContentStrategy.id)).where(
                ContentStrategy.organization_id == organization_id,
                ContentStrategy.business_id == business_id,
                ContentStrategy.archived_at.is_(None),
                ContentStrategy.starts_on <= ends_on,
                ContentStrategy.ends_on >= starts_on,
            )
        )
        or 0
    )
    approved_strategies_total = int(
        session.scalar(
            select(func.count(ContentStrategy.id)).where(
                ContentStrategy.organization_id == organization_id,
                ContentStrategy.business_id == business_id,
                ContentStrategy.archived_at.is_(None),
                ContentStrategy.status == "APPROVED",
                ContentStrategy.starts_on <= ends_on,
                ContentStrategy.ends_on >= starts_on,
            )
        )
        or 0
    )
    calendar_entries_total = int(
        session.scalar(
            select(func.count(CalendarEntry.id)).where(
                CalendarEntry.organization_id == organization_id,
                CalendarEntry.business_id == business_id,
                CalendarEntry.archived_at.is_(None),
                CalendarEntry.suggested_for >= period_start,
                CalendarEntry.suggested_for < period_end,
            )
        )
        or 0
    )

    return PeriodReportRead(
        organization_id=organization_id,
        business_id=business_id,
        starts_on=starts_on,
        ends_on=ends_on,
        content_total=content_total,
        content_by_status=content_by_status,
        content_versions_total=version_total,
        revisions_total=max(version_total - content_total, 0),
        approvals_by_component=approvals_by_component,
        manual_publications_total=manual_publications_total,
        publications_by_channel=publications_by_channel,
        strategies_total=strategies_total,
        approved_strategies_total=approved_strategies_total,
        calendar_entries_total=calendar_entries_total,
        unavailable_metrics=list(_UNAVAILABLE_METRICS),
    )
