from datetime import UTC, datetime, time

from fastapi.testclient import TestClient
from sqlalchemy import select

from growthos.database import get_session_factory
from growthos.domain.enums import (
    NotificationCategory,
    NotificationDeliveryMode,
    NotificationDeliveryStatus,
    NotificationDigestFrequency,
    Role,
)
from growthos.models import (
    AuditLog,
    Job,
    NotificationDelivery,
    NotificationPreference,
)
from growthos.services.email_jobs import enqueue_notification_email
from growthos.services.notification_preferences import (
    digest_period_start,
    next_digest_slot,
)
from growthos.services.notifications import create_notification
from tests.conftest import create_identity, csrf_headers, login


def _preference_payload(
    *,
    daily: set[NotificationCategory] | None = None,
    weekly: set[NotificationCategory] | None = None,
    urgent_only: set[NotificationCategory] | None = None,
    disabled: set[NotificationCategory] | None = None,
) -> dict[str, object]:
    daily = daily or set()
    weekly = weekly or set()
    urgent_only = urgent_only or set()
    disabled = disabled or set()
    categories = []
    for category in NotificationCategory:
        mode = NotificationDeliveryMode.IMMEDIATE
        if category in daily:
            mode = NotificationDeliveryMode.DAILY
        elif category in weekly:
            mode = NotificationDeliveryMode.WEEKLY
        elif category in urgent_only:
            mode = NotificationDeliveryMode.URGENT_ONLY
        categories.append(
            {
                "category": category.value,
                "delivery_mode": mode.value,
                "is_enabled": category not in disabled,
            }
        )
    return {
        "email_enabled": True,
        "timezone": "America/Sao_Paulo",
        "digest_time": "09:30:00",
        "weekly_day": 2,
        "categories": categories,
    }


def test_preferences_are_individual_audited_and_schedule_idempotent_digest_jobs(
    client: TestClient,
) -> None:
    first = create_identity(
        slug="notification-first",
        email="notification-first@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Primeiro cliente",
    )
    second = create_identity(
        slug="notification-second",
        email="notification-second@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Segundo cliente",
    )
    first_csrf = login(client, first)

    default = client.get("/api/v1/notifications/preferences")
    assert default.status_code == 200
    assert default.json()["revision"] == 0
    assert len(default.json()["categories"]) == len(NotificationCategory)

    payload = _preference_payload(
        daily={NotificationCategory.CONTENT_APPROVED},
        weekly={NotificationCategory.REPORT_AVAILABLE},
        disabled={NotificationCategory.PUBLICATION_RECORDED},
    )
    missing_csrf = client.put("/api/v1/notifications/preferences", json=payload)
    assert missing_csrf.status_code == 403
    updated = client.put(
        "/api/v1/notifications/preferences",
        headers=csrf_headers(first_csrf),
        json=payload,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"] == 1
    assert updated.json()["user_id"] == str(first.user_id)
    assert {item["delivery_mode"] for item in updated.json()["categories"]} >= {
        "DAILY",
        "WEEKLY",
    }

    with get_session_factory()() as session:
        preference = session.scalar(
            select(NotificationPreference).where(
                NotificationPreference.organization_id == first.organization_id,
                NotificationPreference.user_id == first.user_id,
            )
        )
        assert preference is not None
        jobs = session.scalars(
            select(Job).where(
                Job.organization_id == first.organization_id,
                Job.type == "notification.digest.prepare",
            )
        ).all()
        assert {job.payload["frequency"] for job in jobs} == {"DAILY", "WEEKLY"}
        assert all(
            set(job.payload)
            == {
                "preference_id",
                "preference_revision",
                "frequency",
                "scheduled_for",
            }
            for job in jobs
        )
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.organization_id == first.organization_id,
                AuditLog.action == "notification.preference_created",
            )
        )
        assert audit is not None
        assert audit.actor_user_id == first.user_id

    login(client, second)
    isolated = client.get("/api/v1/notifications/preferences")
    assert isolated.status_code == 200
    assert isolated.json()["revision"] == 0
    assert isolated.json()["organization_id"] == str(second.organization_id)

    login(client, first)
    persisted = client.get("/api/v1/notifications/preferences")
    assert persisted.status_code == 200
    assert persisted.json()["revision"] == 1


def test_delivery_policy_keeps_internal_notification_and_honors_category_modes(
    client: TestClient,
) -> None:
    identity = create_identity(
        slug="notification-policy",
        email="notification-policy@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente das preferências",
    )
    csrf = login(client, identity)
    payload = _preference_payload(
        daily={NotificationCategory.CONTENT_APPROVED},
        urgent_only={NotificationCategory.CONTENT_AWAITING_APPROVAL},
        disabled={NotificationCategory.PUBLICATION_RECORDED},
    )
    response = client.put(
        "/api/v1/notifications/preferences",
        headers=csrf_headers(csrf),
        json=payload,
    )
    assert response.status_code == 200, response.text

    with get_session_factory()() as session:
        daily = create_notification(
            session,
            organization_id=identity.organization_id,
            business_id=identity.business_id,
            actor_user_id=identity.user_id,
            recipient_user_id=identity.user_id,
            notification_type="CONTENT_DECISION",
            title="Conteúdo aprovado",
            message="Uma aprovação foi registrada.",
            resource_type="content_item",
            resource_id=identity.business_id,
            category=NotificationCategory.CONTENT_APPROVED,
        )
        enqueue_notification_email(session, daily, idempotency_key="daily-not-immediate")

        urgent = create_notification(
            session,
            organization_id=identity.organization_id,
            business_id=identity.business_id,
            actor_user_id=identity.user_id,
            recipient_user_id=identity.user_id,
            notification_type="CONTENT_REVIEW_REQUESTED",
            title="Aprovação pendente",
            message="Existe uma decisão pendente.",
            resource_type="content_item",
            resource_id=identity.business_id,
            category=NotificationCategory.CONTENT_AWAITING_APPROVAL,
        )
        enqueue_notification_email(session, urgent, idempotency_key="urgent-immediate")

        disabled = create_notification(
            session,
            organization_id=identity.organization_id,
            business_id=identity.business_id,
            actor_user_id=identity.user_id,
            recipient_user_id=identity.user_id,
            notification_type="PUBLICATION_RECORDED",
            title="Publicação registrada",
            message="Registro manual concluído.",
            resource_type="content_item",
            resource_id=identity.business_id,
            category=NotificationCategory.PUBLICATION_RECORDED,
        )
        enqueue_notification_email(session, disabled, idempotency_key="disabled-category")
        session.commit()

        immediate_jobs = session.scalars(
            select(Job).where(
                Job.organization_id == identity.organization_id,
                Job.type == "notification.email.smtp",
            )
        ).all()
        assert [job.payload for job in immediate_jobs] == [{"notification_id": str(urgent.id)}]
        assert (
            session.scalar(
                select(NotificationDelivery).where(NotificationDelivery.notification_id == daily.id)
            )
            is None
        )
        skipped = session.scalar(
            select(NotificationDelivery).where(NotificationDelivery.notification_id == disabled.id)
        )
        assert skipped is not None
        assert skipped.status == NotificationDeliveryStatus.SKIPPED
        policy_actions = set(
            session.scalars(
                select(AuditLog.action).where(
                    AuditLog.organization_id == identity.organization_id,
                    AuditLog.resource_type == "notification",
                    AuditLog.resource_id.in_([daily.id, disabled.id]),
                )
            ).all()
        )
        assert {
            "notification.email_deferred_to_digest",
            "notification.email_skipped_by_preference",
        } <= policy_actions

    deliveries = client.get("/api/v1/notifications/deliveries")
    assert deliveries.status_code == 200
    assert {item["notification_id"] for item in deliveries.json()} == {
        str(urgent.id),
        str(disabled.id),
    }


def test_viewer_can_update_only_their_own_notification_preferences(client: TestClient) -> None:
    viewer = create_identity(
        slug="notification-viewer",
        email="notification-viewer@example.test",
        role=Role.VIEWER,
        business_name="Cliente somente leitura",
    )
    csrf = login(client, viewer)

    assert client.get("/api/v1/notifications/preferences").status_code == 200
    updated = client.put(
        "/api/v1/notifications/preferences",
        headers=csrf_headers(csrf),
        json=_preference_payload(),
    )
    assert updated.status_code == 200
    assert updated.json()["user_id"] == str(viewer.user_id)
    with get_session_factory()() as session:
        assert (
            session.scalar(
                select(NotificationPreference).where(
                    NotificationPreference.organization_id == viewer.organization_id,
                    NotificationPreference.user_id == viewer.user_id,
                )
            )
            is not None
        )


def test_onboarding_step_13_materializes_the_actor_preference(client: TestClient) -> None:
    identity = create_identity(
        slug="notification-onboarding",
        email="notification-onboarding@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Cliente em configuração",
    )
    csrf = login(client, identity)
    started = client.post(
        f"/api/v1/businesses/{identity.business_id}/onboarding",
        headers=csrf_headers(csrf),
    )
    assert started.status_code == 200, started.text
    saved = client.put(
        f"/api/v1/businesses/{identity.business_id}/onboarding/steps/13",
        headers=csrf_headers(csrf),
        json={
            "step": 13,
            "revision": started.json()["revision"],
            "email_enabled": True,
            "mode": "DAILY",
            "timezone": "America/Sao_Paulo",
            "digest_time": "08:45:00",
            "weekly_day": 1,
            "disabled_categories": ["REPORT_AVAILABLE"],
        },
    )
    assert saved.status_code == 200, saved.text

    preference = client.get("/api/v1/notifications/preferences")
    assert preference.status_code == 200
    assert preference.json()["digest_time"] == "08:45:00"
    categories = {item["category"]: item for item in preference.json()["categories"]}
    assert categories["CONTENT_APPROVED"]["delivery_mode"] == "DAILY"
    assert categories["REPORT_AVAILABLE"]["is_enabled"] is False


def test_next_digest_slot_respects_user_timezone_and_weekday() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)  # quinta, 09:00 em São Paulo
    daily = next_digest_slot(
        now=now,
        timezone_name="America/Sao_Paulo",
        digest_time=time(9, 30),
        weekly_day=0,
        frequency=NotificationDigestFrequency.DAILY,
    )
    weekly = next_digest_slot(
        now=now,
        timezone_name="America/Sao_Paulo",
        digest_time=time(9, 30),
        weekly_day=0,
        frequency=NotificationDigestFrequency.WEEKLY,
    )

    assert daily == datetime(2026, 7, 16, 12, 30, tzinfo=UTC)
    assert weekly == datetime(2026, 7, 20, 12, 30, tzinfo=UTC)


def test_digest_slots_have_no_gap_across_nonexistent_dst_time() -> None:
    spring_slot = next_digest_slot(
        now=datetime(2026, 3, 8, 6, 0, tzinfo=UTC),
        timezone_name="America/New_York",
        digest_time=time(2, 30),
        weekly_day=0,
        frequency=NotificationDigestFrequency.DAILY,
    )
    next_day_slot = next_digest_slot(
        now=spring_slot,
        timezone_name="America/New_York",
        digest_time=time(2, 30),
        weekly_day=0,
        frequency=NotificationDigestFrequency.DAILY,
    )
    previous = digest_period_start(
        period_end=next_day_slot,
        timezone_name="America/New_York",
        digest_time=time(2, 30),
        weekly_day=0,
        frequency=NotificationDigestFrequency.DAILY,
    )

    # 02:30 não existe neste dia; a política usa o primeiro instante válido,
    # 03:00 local, sem inventar uma janela fixa de 24 horas em UTC.
    assert spring_slot == datetime(2026, 3, 8, 7, 0, tzinfo=UTC)
    assert next_day_slot == datetime(2026, 3, 9, 6, 30, tzinfo=UTC)
    assert previous == spring_slot


def test_digest_slots_choose_later_occurrence_for_ambiguous_dst_time() -> None:
    repeated_slot = next_digest_slot(
        now=datetime(2026, 11, 1, 4, 0, tzinfo=UTC),
        timezone_name="America/New_York",
        digest_time=time(1, 30),
        weekly_day=0,
        frequency=NotificationDigestFrequency.DAILY,
    )
    next_day_slot = next_digest_slot(
        now=repeated_slot,
        timezone_name="America/New_York",
        digest_time=time(1, 30),
        weekly_day=0,
        frequency=NotificationDigestFrequency.DAILY,
    )

    assert repeated_slot == datetime(2026, 11, 1, 6, 30, tzinfo=UTC)
    assert (
        digest_period_start(
            period_end=next_day_slot,
            timezone_name="America/New_York",
            digest_time=time(1, 30),
            weekly_day=0,
            frequency=NotificationDigestFrequency.DAILY,
        )
        == repeated_slot
    )
