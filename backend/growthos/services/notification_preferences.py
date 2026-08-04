from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from growthos.domain.enums import (
    JobStatus,
    NotificationCategory,
    NotificationDeliveryMode,
    NotificationDigestFrequency,
)
from growthos.models import (
    Job,
    NotificationCategoryPreference,
    NotificationPreference,
)
from growthos.schemas_notifications import (
    NotificationCategoryPreferenceInput,
    NotificationCategoryPreferenceRead,
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
)
from growthos.services.audit import add_audit_log


def default_preference_payload() -> NotificationPreferenceUpdate:
    return NotificationPreferenceUpdate(
        categories=[
            NotificationCategoryPreferenceInput(category=category)
            for category in NotificationCategory
        ]
    )


def read_notification_preference(
    session: Session,
    *,
    organization_id: UUID,
    user_id: UUID,
) -> NotificationPreferenceRead:
    preference = session.scalar(
        select(NotificationPreference).where(
            NotificationPreference.organization_id == organization_id,
            NotificationPreference.user_id == user_id,
        )
    )
    if preference is None:
        payload = default_preference_payload()
        return NotificationPreferenceRead(
            id=None,
            organization_id=organization_id,
            user_id=user_id,
            email_enabled=payload.email_enabled,
            timezone=payload.timezone,
            digest_time=payload.digest_time,
            weekly_day=payload.weekly_day,
            revision=0,
            categories=[
                NotificationCategoryPreferenceRead(id=None, **item.model_dump())
                for item in payload.categories
            ],
            created_at=None,
            updated_at=None,
        )
    categories = list(
        session.scalars(
            select(NotificationCategoryPreference)
            .where(
                NotificationCategoryPreference.preference_id == preference.id,
                NotificationCategoryPreference.organization_id == organization_id,
                NotificationCategoryPreference.user_id == user_id,
            )
            .order_by(NotificationCategoryPreference.category)
        ).all()
    )
    by_category = {item.category: item for item in categories}
    serialized_categories = [
        NotificationCategoryPreferenceRead.model_validate(by_category[category])
        if category in by_category
        else NotificationCategoryPreferenceRead(
            id=None,
            category=category,
            delivery_mode=NotificationDeliveryMode.IMMEDIATE,
            is_enabled=True,
        )
        for category in NotificationCategory
    ]
    return NotificationPreferenceRead(
        id=preference.id,
        organization_id=preference.organization_id,
        user_id=preference.user_id,
        email_enabled=preference.email_enabled,
        timezone=preference.timezone,
        digest_time=preference.digest_time,
        weekly_day=preference.weekly_day,
        revision=preference.revision,
        categories=serialized_categories,
        created_at=preference.created_at,
        updated_at=preference.updated_at,
    )


def upsert_notification_preference(
    session: Session,
    *,
    organization_id: UUID,
    user_id: UUID,
    actor_user_id: UUID,
    payload: NotificationPreferenceUpdate,
    business_id: UUID | None = None,
    now: datetime | None = None,
) -> NotificationPreferenceRead:
    preference = session.scalar(
        select(NotificationPreference)
        .where(
            NotificationPreference.organization_id == organization_id,
            NotificationPreference.user_id == user_id,
        )
        .with_for_update()
    )
    created = preference is None
    if preference is None:
        preference = NotificationPreference(
            organization_id=organization_id,
            user_id=user_id,
            revision=1,
        )
        session.add(preference)
    else:
        preference.revision += 1
    preference.email_enabled = payload.email_enabled
    preference.timezone = payload.timezone
    preference.digest_time = payload.digest_time
    preference.weekly_day = payload.weekly_day
    session.flush()

    stored_categories = {
        item.category: item
        for item in session.scalars(
            select(NotificationCategoryPreference).where(
                NotificationCategoryPreference.preference_id == preference.id,
                NotificationCategoryPreference.organization_id == organization_id,
                NotificationCategoryPreference.user_id == user_id,
            )
        ).all()
    }
    requested = {item.category: item for item in payload.categories}
    for category in NotificationCategory:
        category_payload = requested.get(
            category,
            NotificationCategoryPreferenceInput(category=category),
        )
        category_preference = stored_categories.get(category)
        if category_preference is None:
            category_preference = NotificationCategoryPreference(
                preference_id=preference.id,
                organization_id=organization_id,
                user_id=user_id,
                category=category,
            )
            session.add(category_preference)
        category_preference.delivery_mode = category_payload.delivery_mode
        category_preference.is_enabled = category_payload.is_enabled

    session.flush()
    _enqueue_digest_schedules(
        session,
        preference=preference,
        payload=payload,
        now=now or datetime.now(UTC),
    )
    add_audit_log(
        session,
        organization_id=organization_id,
        business_id=business_id,
        actor_user_id=actor_user_id,
        action=(
            "notification.preference_created" if created else "notification.preference_updated"
        ),
        resource_type="notification_preference",
        resource_id=preference.id,
        details={
            "revision": preference.revision,
            "email_enabled": preference.email_enabled,
            "timezone": preference.timezone,
            "daily_categories": _count_mode(payload, NotificationDeliveryMode.DAILY),
            "weekly_categories": _count_mode(payload, NotificationDeliveryMode.WEEKLY),
            "disabled_categories": sum(not item.is_enabled for item in payload.categories),
        },
    )
    session.flush()
    return read_notification_preference(
        session,
        organization_id=organization_id,
        user_id=user_id,
    )


def next_digest_slot(
    *,
    now: datetime,
    timezone_name: str,
    digest_time: time,
    weekly_day: int,
    frequency: NotificationDigestFrequency,
) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now deve informar fuso horário")
    zone = ZoneInfo(timezone_name)
    local_now = now.astimezone(zone)
    now_utc = now.astimezone(UTC)
    if frequency == NotificationDigestFrequency.DAILY:
        candidate_date = local_now.date()
        candidate = _local_slot(candidate_date, digest_time, zone)
        if candidate.astimezone(UTC) <= now_utc:
            candidate = _local_slot(candidate_date + timedelta(days=1), digest_time, zone)
    else:
        days_ahead = (weekly_day - local_now.weekday()) % 7
        candidate_date = local_now.date() + timedelta(days=days_ahead)
        candidate = _local_slot(candidate_date, digest_time, zone)
        if candidate.astimezone(UTC) <= now_utc:
            candidate = _local_slot(candidate_date + timedelta(days=7), digest_time, zone)
    return candidate.astimezone(UTC)


def digest_period_start(
    *,
    period_end: datetime,
    timezone_name: str,
    digest_time: time,
    weekly_day: int,
    frequency: NotificationDigestFrequency,
) -> datetime:
    """Retorna o slot local anterior sem presumir que o dia sempre tem 24 horas."""

    if period_end.tzinfo is None or period_end.utcoffset() is None:
        raise ValueError("period_end deve informar fuso horário")
    zone = ZoneInfo(timezone_name)
    end_utc = period_end.astimezone(UTC)
    local_end = end_utc.astimezone(zone)
    if frequency == NotificationDigestFrequency.WEEKLY and local_end.date().weekday() != weekly_day:
        raise ValueError("o slot semanal não corresponde ao dia configurado")
    configured_end = _local_slot(local_end.date(), digest_time, zone).astimezone(UTC)
    if configured_end != end_utc:
        raise ValueError("o slot não corresponde ao horário configurado")
    days = 1 if frequency == NotificationDigestFrequency.DAILY else 7
    previous_date = local_end.date() - timedelta(days=days)
    return _local_slot(previous_date, digest_time, zone).astimezone(UTC)


def _local_slot(day: date, digest_time: time, timezone: ZoneInfo) -> datetime:
    requested = datetime.combine(day, digest_time.replace(tzinfo=None))
    # Em horário ambíguo escolhemos a segunda ocorrência (fold=1), evitando
    # disparar antes de o relógio local terminar a repetição. Em horário
    # inexistente avançamos até o primeiro instante local válido.
    for minute_offset in range(26 * 60):
        candidate_naive = requested + timedelta(minutes=minute_offset)
        valid: dict[datetime, datetime] = {}
        for fold in (0, 1):
            candidate = candidate_naive.replace(tzinfo=timezone, fold=fold)
            utc_candidate = candidate.astimezone(UTC)
            round_trip = utc_candidate.astimezone(timezone)
            if round_trip.replace(tzinfo=None) == candidate_naive:
                valid[utc_candidate] = candidate
        if valid:
            return valid[max(valid)]
    raise ValueError("não foi possível resolver o horário local configurado")


def _count_mode(
    payload: NotificationPreferenceUpdate,
    mode: NotificationDeliveryMode,
) -> int:
    return sum(item.is_enabled and item.delivery_mode == mode for item in payload.categories)


def _enqueue_digest_schedules(
    session: Session,
    *,
    preference: NotificationPreference,
    payload: NotificationPreferenceUpdate,
    now: datetime,
) -> None:
    if not preference.email_enabled:
        return
    for frequency in NotificationDigestFrequency:
        mode = NotificationDeliveryMode(frequency.value)
        if _count_mode(payload, mode) == 0:
            continue
        scheduled_for = next_digest_slot(
            now=now,
            timezone_name=preference.timezone,
            digest_time=preference.digest_time,
            weekly_day=preference.weekly_day,
            frequency=frequency,
        )
        idempotency_key = (
            f"notification-digest:{preference.id}:{preference.revision}:"
            f"{frequency.value}:{scheduled_for.isoformat()}"
        )
        existing = session.scalar(
            select(Job.id).where(
                Job.organization_id == preference.organization_id,
                Job.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            continue
        session.add(
            Job(
                organization_id=preference.organization_id,
                type="notification.digest.prepare",
                status=JobStatus.PENDING,
                payload={
                    "preference_id": str(preference.id),
                    "preference_revision": preference.revision,
                    "frequency": frequency.value,
                    "scheduled_for": scheduled_for.isoformat(),
                },
                idempotency_key=idempotency_key,
                available_at=scheduled_for,
                max_attempts=5,
            )
        )
