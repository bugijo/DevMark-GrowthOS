from sqlalchemy import func, select

from growthos.database import get_session_factory
from growthos.models import (
    Approval,
    AudienceSegment,
    CalendarEntry,
    ContentItem,
    ContentPlan,
    ContentStrategy,
    MarketingObjective,
    Membership,
    Notification,
    Organization,
    Service,
    StrategyVersion,
    User,
    VisualPreset,
)
from growthos.seed import seed_demo


def test_seed_is_idempotent_and_uses_distinct_client_credentials() -> None:
    with get_session_factory()() as session:
        first = seed_demo(session)
        second = seed_demo(session)
        assert first == second
        assert session.scalar(select(func.count()).select_from(Organization)) == 1
        assert session.scalar(select(func.count()).select_from(User)) == 2
        assert session.scalar(select(func.count()).select_from(Membership)) == 2
        assert session.scalar(select(func.count()).select_from(Service)) == 1
        assert session.scalar(select(func.count()).select_from(AudienceSegment)) == 1
        assert session.scalar(select(func.count()).select_from(MarketingObjective)) == 1
        assert session.scalar(select(func.count()).select_from(VisualPreset)) == 1
        assert session.scalar(select(func.count()).select_from(ContentStrategy)) == 1
        assert session.scalar(select(func.count()).select_from(StrategyVersion)) == 1
        assert session.scalar(select(func.count()).select_from(ContentPlan)) == 1
        assert session.scalar(select(func.count()).select_from(CalendarEntry)) == 1
        assert session.scalar(select(func.count()).select_from(ContentItem)) == 1
        assert session.scalar(select(func.count()).select_from(Approval)) == 2
        assert session.scalar(select(func.count()).select_from(Notification)) == 1
        content = session.scalar(select(ContentItem))
        assert content is not None
        assert content.status.value == "PUBLISHED"
        assert content.publication_channel == "Instagram"
        client = session.scalar(select(User).where(User.email == "client@clinicafeliz.local"))
        assert client is not None
        admin = session.scalar(select(User).where(User.email == "admin@devmark.local"))
        assert admin is not None
        assert client.password_hash != admin.password_hash
