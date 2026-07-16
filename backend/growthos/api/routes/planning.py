from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from growthos.database import get_session
from growthos.dependencies import (
    AuthContext,
    get_current_context,
    get_scoped_business,
    require_capability,
    require_csrf,
)
from growthos.domain.enums import JobStatus, Role
from growthos.domain.permissions import Capability
from growthos.models import (
    AudienceSegment,
    BrandProfile,
    CalendarEntry,
    ContentPlan,
    ContentStrategy,
    Job,
    MarketingObjective,
    Membership,
    Notification,
    Service,
    StrategyVersion,
    User,
    VisualPreset,
)
from growthos.schemas_planning import (
    CalendarEntryCreate,
    CalendarEntryRead,
    CalendarEntryUpdate,
    ContentPlanCreate,
    ContentPlanRead,
    StrategyCreate,
    StrategyDecision,
    StrategyRead,
    StrategyVersionInput,
    StrategyVersionRead,
)
from growthos.services.audit import add_audit_log
from growthos.services.strategy_provider import MockStrategyProvider, StrategyGenerationRequest

router = APIRouter()


def _strategy(
    session: Session,
    context: AuthContext,
    strategy_id: UUID,
    *,
    lock: bool = False,
) -> ContentStrategy:
    query = select(ContentStrategy).where(
        ContentStrategy.id == strategy_id,
        ContentStrategy.organization_id == context.organization.id,
        ContentStrategy.archived_at.is_(None),
    )
    if lock:
        query = query.with_for_update()
    strategy = session.scalar(query)
    if strategy is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estratégia não encontrada")
    get_scoped_business(session, context, strategy.business_id)
    return strategy


def _strategy_version(
    session: Session,
    strategy: ContentStrategy,
    version_id: UUID | None,
) -> StrategyVersion:
    version = session.scalar(
        select(StrategyVersion).where(
            StrategyVersion.id == version_id,
            StrategyVersion.content_strategy_id == strategy.id,
            StrategyVersion.organization_id == strategy.organization_id,
            StrategyVersion.business_id == strategy.business_id,
        )
    )
    if version is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Estratégia sem versão válida")
    return version


def _serialize_strategy(session: Session, strategy: ContentStrategy) -> StrategyRead:
    version = _strategy_version(session, strategy, strategy.current_version_id)
    return StrategyRead(
        id=strategy.id,
        organization_id=strategy.organization_id,
        business_id=strategy.business_id,
        name=strategy.name,
        starts_on=strategy.starts_on,
        ends_on=strategy.ends_on,
        status=strategy.status,
        current_version=StrategyVersionRead.model_validate(version),
        approved_version_id=strategy.approved_version_id,
        decision_comment=strategy.decision_comment,
        submitted_at=strategy.submitted_at,
        decided_at=strategy.decided_at,
        created_at=strategy.created_at,
        updated_at=strategy.updated_at,
    )


def _snapshot_rows(
    session: Session,
    model: type[Service] | type[AudienceSegment] | type[MarketingObjective],
    ids: list[UUID],
    organization_id: UUID,
    business_id: UUID,
) -> list[dict[str, Any]]:
    if not ids:
        return []
    unique_ids = set(ids)
    rows: list[Any] = list(
        session.scalars(
            select(model).where(
                model.id.in_(unique_ids),
                model.organization_id == organization_id,
                model.business_id == business_id,
                model.is_active.is_(True),
            )
        ).all()
    )
    if len(rows) != len(unique_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Catálogo inválido")
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "description": row.description,
        }
        for row in rows
    ]


def _create_version(
    session: Session,
    context: AuthContext,
    strategy: ContentStrategy,
    payload: StrategyVersionInput,
) -> StrategyVersion:
    brand = session.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == context.organization.id,
            BrandProfile.business_id == strategy.business_id,
        )
    )
    if brand is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cadastre o Brand Kit antes da estratégia")
    services = _snapshot_rows(
        session,
        Service,
        payload.service_ids,
        context.organization.id,
        strategy.business_id,
    )
    audiences = _snapshot_rows(
        session,
        AudienceSegment,
        payload.audience_ids,
        context.organization.id,
        strategy.business_id,
    )
    objectives = _snapshot_rows(
        session,
        MarketingObjective,
        payload.marketing_objective_ids,
        context.organization.id,
        strategy.business_id,
    )
    generated = MockStrategyProvider().generate(
        StrategyGenerationRequest(
            brand_name=brand.brand_name,
            objective=payload.objective,
            positioning=payload.positioning,
            funnel=tuple(payload.funnel),
            channels=tuple(payload.channels),
            pillars=tuple(payload.pillars),
            planned_indicators=tuple(payload.planned_indicators),
        )
    )
    previous = (
        _strategy_version(session, strategy, strategy.current_version_id)
        if strategy.current_version_id
        else None
    )
    version = StrategyVersion(
        organization_id=context.organization.id,
        business_id=strategy.business_id,
        content_strategy_id=strategy.id,
        version_number=(previous.version_number + 1) if previous else 1,
        objective=payload.objective.strip(),
        positioning=generated.positioning,
        funnel=list(generated.funnel),
        channels=list(generated.channels),
        pillars=list(generated.pillars),
        planned_indicators=list(generated.planned_indicators),
        service_snapshots=services,
        audience_snapshots=audiences,
        objective_snapshots=objectives,
        brand_context_snapshot={
            "brand_name": brand.brand_name,
            "tone_of_voice": brand.tone_of_voice,
            "primary_colors": brand.primary_colors,
            "differentiators": brand.differentiators,
        },
        source="MOCK",
        provider_name=generated.provider_name,
        provider_reference=generated.provider_reference,
        created_by_user_id=context.user.id,
        supersedes_version_id=previous.id if previous else None,
    )
    session.add(version)
    session.flush()
    strategy.current_version_id = version.id
    strategy.status = "DRAFT"
    strategy.submitted_by_user_id = None
    strategy.submitted_at = None
    strategy.decided_by_user_id = None
    strategy.decided_at = None
    strategy.decision_comment = None
    return version


def _email_job(
    session: Session,
    *,
    organization_id: UUID,
    user: User,
    subject: str,
    text: str,
    key: str,
) -> None:
    session.add(
        Job(
            organization_id=organization_id,
            type="notification.email.smtp",
            status=JobStatus.PENDING,
            payload={"to": user.email, "subject": subject, "text": text},
            idempotency_key=key,
        )
    )


@router.get(
    "/businesses/{business_id}/strategies",
    response_model=list[StrategyRead],
)
def list_strategies(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[StrategyRead]:
    require_capability(context, Capability.STRATEGY_VIEW)
    business = get_scoped_business(session, context, business_id)
    query = select(ContentStrategy).where(
        ContentStrategy.organization_id == context.organization.id,
        ContentStrategy.business_id == business.id,
        ContentStrategy.archived_at.is_(None),
    )
    if context.membership.role in {Role.CLIENT_OWNER, Role.CLIENT_REVIEWER}:
        query = query.where(ContentStrategy.status.in_(["CLIENT_REVIEW", "APPROVED"]))
    elif context.membership.role == Role.VIEWER:
        query = query.where(ContentStrategy.status == "APPROVED")
    strategies = session.scalars(query.order_by(ContentStrategy.starts_on.desc())).all()
    return [_serialize_strategy(session, strategy) for strategy in strategies]


@router.post(
    "/businesses/{business_id}/strategies",
    response_model=StrategyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_strategy(
    business_id: UUID,
    payload: StrategyCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> StrategyRead:
    require_capability(context, Capability.STRATEGY_MANAGE)
    business = get_scoped_business(session, context, business_id)
    strategy = ContentStrategy(
        organization_id=context.organization.id,
        business_id=business.id,
        name=payload.name.strip(),
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
        status="DRAFT",
        created_by_user_id=context.user.id,
    )
    session.add(strategy)
    session.flush()
    version = _create_version(session, context, strategy, payload)
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="strategy.created",
        resource_type="content_strategy",
        resource_id=strategy.id,
        details={"version_id": str(version.id), "provider": version.provider_name},
    )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Estratégia já cadastrada") from exc
    return _serialize_strategy(session, strategy)


@router.post("/strategies/{strategy_id}/versions", response_model=StrategyRead)
def create_strategy_version(
    strategy_id: UUID,
    payload: StrategyVersionInput,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> StrategyRead:
    require_capability(context, Capability.STRATEGY_MANAGE)
    strategy = _strategy(session, context, strategy_id, lock=True)
    if strategy.status not in {"DRAFT", "APPROVED"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Estratégia está em revisão")
    version = _create_version(session, context, strategy, payload)
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=strategy.business_id,
        actor_user_id=context.user.id,
        action="strategy.version_created",
        resource_type="strategy_version",
        resource_id=version.id,
        details={"version_number": version.version_number},
    )
    session.commit()
    return _serialize_strategy(session, strategy)


@router.post("/strategies/{strategy_id}/submit-internal", response_model=StrategyRead)
def submit_strategy_internal(
    strategy_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> StrategyRead:
    require_capability(context, Capability.STRATEGY_MANAGE)
    strategy = _strategy(session, context, strategy_id, lock=True)
    if strategy.status != "DRAFT":
        raise HTTPException(status.HTTP_409_CONFLICT, "Transição de estratégia inválida")
    strategy.status = "INTERNAL_REVIEW"
    strategy.submitted_by_user_id = context.user.id
    strategy.submitted_at = datetime.now(UTC)
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=strategy.business_id,
        actor_user_id=context.user.id,
        action="strategy.submitted_internal",
        resource_type="content_strategy",
        resource_id=strategy.id,
    )
    session.commit()
    return _serialize_strategy(session, strategy)


@router.post("/strategies/{strategy_id}/send-to-client", response_model=StrategyRead)
def send_strategy_to_client(
    strategy_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> StrategyRead:
    require_capability(context, Capability.STRATEGY_REVIEW_INTERNAL)
    strategy = _strategy(session, context, strategy_id, lock=True)
    if strategy.status != "INTERNAL_REVIEW":
        raise HTTPException(status.HTTP_409_CONFLICT, "Transição de estratégia inválida")
    strategy.status = "CLIENT_REVIEW"
    reviewers = session.execute(
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.organization_id == context.organization.id,
            Membership.business_id == strategy.business_id,
            Membership.role.in_([Role.CLIENT_OWNER, Role.CLIENT_REVIEWER]),
            Membership.is_active.is_(True),
            User.is_active.is_(True),
        )
    ).all()
    for user, membership in reviewers:
        session.add(
            Notification(
                organization_id=context.organization.id,
                business_id=strategy.business_id,
                recipient_user_id=user.id,
                type="STRATEGY_REVIEW",
                title="Estratégia aguardando aprovação",
                message="A estratégia mensal está pronta para sua revisão.",
                resource_type="content_strategy",
                resource_id=strategy.id,
            )
        )
        _email_job(
            session,
            organization_id=context.organization.id,
            user=user,
            subject="Estratégia aguardando aprovação",
            text="Entre no GrowthOS para revisar a estratégia mensal.",
            key=f"strategy-review:{strategy.id}:{membership.id}",
        )
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=strategy.business_id,
        actor_user_id=context.user.id,
        action="strategy.sent_to_client",
        resource_type="content_strategy",
        resource_id=strategy.id,
        details={"reviewer_count": len(reviewers)},
    )
    session.commit()
    return _serialize_strategy(session, strategy)


@router.post("/strategies/{strategy_id}/decision", response_model=StrategyRead)
def decide_strategy(
    strategy_id: UUID,
    payload: StrategyDecision,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> StrategyRead:
    require_capability(context, Capability.STRATEGY_DECIDE_CLIENT)
    strategy = _strategy(session, context, strategy_id, lock=True)
    if strategy.status != "CLIENT_REVIEW":
        raise HTTPException(status.HTTP_409_CONFLICT, "Estratégia não aguarda decisão")
    now = datetime.now(UTC)
    strategy.decided_by_user_id = context.user.id
    strategy.decided_at = now
    strategy.decision_comment = payload.comment
    if payload.decision == "APPROVE":
        strategy.status = "APPROVED"
        strategy.approved_version_id = strategy.current_version_id
        action = "strategy.approved_by_client"
    else:
        strategy.status = "DRAFT"
        action = "strategy.changes_requested"
    internal_users = session.scalars(
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.organization_id == context.organization.id,
            Membership.business_id.is_(None),
            Membership.role.in_([Role.AGENCY_ADMIN, Role.STRATEGIST]),
            Membership.is_active.is_(True),
            User.is_active.is_(True),
        )
    ).all()
    for user in internal_users:
        session.add(
            Notification(
                organization_id=context.organization.id,
                business_id=strategy.business_id,
                recipient_user_id=user.id,
                type="STRATEGY_DECISION",
                title="Decisão do cliente sobre a estratégia",
                message=(
                    "A estratégia foi aprovada."
                    if payload.decision == "APPROVE"
                    else "O cliente pediu alterações na estratégia."
                ),
                resource_type="content_strategy",
                resource_id=strategy.id,
            )
        )
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=strategy.business_id,
        actor_user_id=context.user.id,
        action=action,
        resource_type="content_strategy",
        resource_id=strategy.id,
        details={"version_id": str(strategy.current_version_id)},
    )
    session.commit()
    return _serialize_strategy(session, strategy)


def _plan(session: Session, context: AuthContext, plan_id: UUID) -> ContentPlan:
    plan = session.scalar(
        select(ContentPlan).where(
            ContentPlan.id == plan_id,
            ContentPlan.organization_id == context.organization.id,
            ContentPlan.archived_at.is_(None),
        )
    )
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plano não encontrado")
    get_scoped_business(session, context, plan.business_id)
    return plan


@router.get("/businesses/{business_id}/plans", response_model=list[ContentPlanRead])
def list_plans(
    business_id: UUID,
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[ContentPlan]:
    require_capability(context, Capability.CALENDAR_VIEW)
    business = get_scoped_business(session, context, business_id)
    return list(
        session.scalars(
            select(ContentPlan)
            .where(
                ContentPlan.organization_id == context.organization.id,
                ContentPlan.business_id == business.id,
                ContentPlan.archived_at.is_(None),
            )
            .order_by(ContentPlan.starts_on.desc())
        ).all()
    )


@router.post(
    "/businesses/{business_id}/plans",
    response_model=ContentPlanRead,
    status_code=status.HTTP_201_CREATED,
)
def create_plan(
    business_id: UUID,
    payload: ContentPlanCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> ContentPlan:
    require_capability(context, Capability.CALENDAR_MANAGE)
    business = get_scoped_business(session, context, business_id)
    strategy = _strategy(session, context, payload.strategy_id)
    if strategy.business_id != business.id or strategy.status != "APPROVED":
        raise HTTPException(status.HTTP_409_CONFLICT, "A estratégia precisa estar aprovada")
    if payload.starts_on < strategy.starts_on or payload.ends_on > strategy.ends_on:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Período fora da estratégia")
    assert strategy.approved_version_id is not None
    plan = ContentPlan(
        organization_id=context.organization.id,
        business_id=business.id,
        content_strategy_id=strategy.id,
        strategy_version_id=strategy.approved_version_id,
        name=payload.name.strip(),
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
        frequency=payload.frequency.strip().upper(),
        status="ACTIVE",
        created_by_user_id=context.user.id,
    )
    session.add(plan)
    session.flush()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=business.id,
        actor_user_id=context.user.id,
        action="content_plan.created",
        resource_type="content_plan",
        resource_id=plan.id,
    )
    session.commit()
    return plan


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "A data deve conter fuso horário",
        )
    return value.astimezone(UTC)


def _validate_preset(
    session: Session,
    context: AuthContext,
    business_id: UUID,
    preset_id: UUID | None,
) -> None:
    if preset_id is None:
        return
    exists = session.scalar(
        select(VisualPreset.id).where(
            VisualPreset.id == preset_id,
            VisualPreset.organization_id == context.organization.id,
            VisualPreset.business_id == business_id,
            VisualPreset.is_active.is_(True),
        )
    )
    if exists is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Preset visual inválido")


@router.post(
    "/plans/{plan_id}/entries",
    response_model=CalendarEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_calendar_entry(
    plan_id: UUID,
    payload: CalendarEntryCreate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> CalendarEntry:
    require_capability(context, Capability.CALENDAR_MANAGE)
    plan = _plan(session, context, plan_id)
    suggested_for = _aware(payload.suggested_for)
    if suggested_for.date() < plan.starts_on or suggested_for.date() > plan.ends_on:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Data fora do plano")
    _validate_preset(session, context, plan.business_id, payload.visual_preset_id)
    entry = CalendarEntry(
        organization_id=context.organization.id,
        business_id=plan.business_id,
        content_plan_id=plan.id,
        visual_preset_id=payload.visual_preset_id,
        title=payload.title.strip(),
        objective=payload.objective.strip(),
        audience=payload.audience.strip(),
        channel=payload.channel.strip().upper(),
        format=payload.format.strip().upper(),
        suggested_for=suggested_for,
        status="PLANNED",
        notes=payload.notes.strip(),
        created_by_user_id=context.user.id,
    )
    session.add(entry)
    session.flush()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=plan.business_id,
        actor_user_id=context.user.id,
        action="calendar_entry.created",
        resource_type="calendar_entry",
        resource_id=entry.id,
    )
    session.commit()
    return entry


@router.post("/plans/{plan_id}/generate-mock", response_model=list[CalendarEntryRead])
def generate_calendar_mock(
    plan_id: UUID,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> list[CalendarEntry]:
    require_capability(context, Capability.CALENDAR_MANAGE)
    plan = _plan(session, context, plan_id)
    existing = session.scalar(
        select(CalendarEntry.id).where(
            CalendarEntry.organization_id == context.organization.id,
            CalendarEntry.content_plan_id == plan.id,
            CalendarEntry.archived_at.is_(None),
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "O plano já possui pautas")
    version = session.get(StrategyVersion, plan.strategy_version_id)
    if version is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Versão da estratégia indisponível")
    pillars = [str(item) for item in version.pillars] or [version.objective]
    channels = version.channels or ["INSTAGRAM"]
    entries: list[CalendarEntry] = []
    current = plan.starts_on
    index = 0
    while current <= plan.ends_on:
        entry = CalendarEntry(
            organization_id=context.organization.id,
            business_id=plan.business_id,
            content_plan_id=plan.id,
            title=f"{pillars[index % len(pillars)]} — semana {index + 1}",
            objective=version.objective,
            audience=(
                str(version.audience_snapshots[0].get("name", ""))
                if version.audience_snapshots
                else ""
            ),
            channel=str(channels[index % len(channels)]).upper(),
            format="FEED",
            suggested_for=datetime.combine(current, time(hour=12), tzinfo=UTC),
            status="GENERATED",
            notes="Pauta criada pelo provider mock; requer revisão humana.",
            sort_order=index,
            created_by_user_id=context.user.id,
        )
        session.add(entry)
        entries.append(entry)
        index += 1
        current += timedelta(days=7)
    session.flush()
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=plan.business_id,
        actor_user_id=context.user.id,
        action="calendar.generated_mock",
        resource_type="content_plan",
        resource_id=plan.id,
        details={"entry_count": len(entries), "provider": "mock"},
    )
    session.commit()
    return entries


@router.get(
    "/businesses/{business_id}/calendar",
    response_model=list[CalendarEntryRead],
)
def list_calendar(
    business_id: UUID,
    starts_on: date = Query(...),
    ends_on: date = Query(...),
    context: AuthContext = Depends(get_current_context),
    session: Session = Depends(get_session),
) -> list[CalendarEntry]:
    require_capability(context, Capability.CALENDAR_VIEW)
    business = get_scoped_business(session, context, business_id)
    if starts_on > ends_on or (ends_on - starts_on).days > 366:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Período inválido")
    start = datetime.combine(starts_on, time.min, tzinfo=UTC)
    end = datetime.combine(ends_on + timedelta(days=1), time.min, tzinfo=UTC)
    return list(
        session.scalars(
            select(CalendarEntry)
            .where(
                CalendarEntry.organization_id == context.organization.id,
                CalendarEntry.business_id == business.id,
                CalendarEntry.archived_at.is_(None),
                CalendarEntry.suggested_for >= start,
                CalendarEntry.suggested_for < end,
            )
            .order_by(CalendarEntry.suggested_for, CalendarEntry.sort_order)
        ).all()
    )


@router.patch("/calendar/{entry_id}", response_model=CalendarEntryRead)
def update_calendar_entry(
    entry_id: UUID,
    payload: CalendarEntryUpdate,
    context: AuthContext = Depends(require_csrf),
    session: Session = Depends(get_session),
) -> CalendarEntry:
    require_capability(context, Capability.CALENDAR_MANAGE)
    entry = session.scalar(
        select(CalendarEntry).where(
            CalendarEntry.id == entry_id,
            CalendarEntry.organization_id == context.organization.id,
            CalendarEntry.archived_at.is_(None),
        )
    )
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pauta não encontrada")
    get_scoped_business(session, context, entry.business_id)
    plan = _plan(session, context, entry.content_plan_id)
    changes = payload.model_dump(exclude_unset=True)
    if "suggested_for" in changes and changes["suggested_for"] is not None:
        changes["suggested_for"] = _aware(changes["suggested_for"])
        if not plan.starts_on <= changes["suggested_for"].date() <= plan.ends_on:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Data fora do plano")
    if "visual_preset_id" in changes:
        _validate_preset(session, context, entry.business_id, changes["visual_preset_id"])
    for field, value in changes.items():
        if isinstance(value, str):
            value = value.strip()
            if field in {"channel", "format"}:
                value = value.upper()
        setattr(entry, field, value)
    add_audit_log(
        session,
        organization_id=context.organization.id,
        business_id=entry.business_id,
        actor_user_id=context.user.id,
        action="calendar_entry.updated",
        resource_type="calendar_entry",
        resource_id=entry.id,
        details={"fields": sorted(changes)},
    )
    session.commit()
    return entry
