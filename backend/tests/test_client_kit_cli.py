import json

from sqlalchemy import func, select

from growthos.client_kit_cli import main
from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import AuditLog, Business, LandingPage
from tests.conftest import create_identity


def _input_file(tmp_path, *, name: str = "Clínica Feliz", segment: str = "Veterinária", slug: str = "clinica-feliz"):
    path = tmp_path / "client.json"
    path.write_text(json.dumps({"name": name, "segment": segment, "slug": slug}), encoding="utf-8")
    return path


def test_client_kit_creates_business_and_draft_demo_landing(tmp_path) -> None:
    agency = create_identity(
        slug="kit-agency", email="kit-agency@example.test", role=Role.AGENCY_ADMIN
    )

    result = main(["--org", "kit-agency", str(_input_file(tmp_path))])

    assert result == 0
    with get_session_factory()() as session:
        business = session.scalar(
            select(Business).where(
                Business.organization_id == agency.organization_id,
                Business.name == "Clínica Feliz",
            )
        )
        assert business is not None
        landing = session.scalar(
            select(LandingPage).where(LandingPage.business_id == business.id)
        )
        assert landing is not None
        assert landing.slug == "clinica-feliz"
        assert landing.status == "DRAFT"
        assert landing.demo_mode is True
        assert landing.price_items == []
        assert landing.whatsapp_number == ""
        assert landing.approved_at is None
        assert session.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.organization_id == agency.organization_id,
                AuditLog.action == "client_kit.provisioned",
            )
        ) == 1


def test_client_kit_is_idempotent(tmp_path) -> None:
    agency = create_identity(
        slug="kit-idempotent", email="kit-idempotent@example.test", role=Role.AGENCY_ADMIN
    )
    input_path = _input_file(tmp_path)

    assert main(["--org", "kit-idempotent", str(input_path)]) == 0
    assert main(["--org", "kit-idempotent", str(input_path)]) == 0

    with get_session_factory()() as session:
        assert session.scalar(
            select(func.count(Business.id)).where(
                Business.organization_id == agency.organization_id,
                Business.name == "Clínica Feliz",
            )
        ) == 1
        business = session.scalar(
            select(Business).where(
                Business.organization_id == agency.organization_id,
                Business.name == "Clínica Feliz",
            )
        )
        assert business is not None
        assert session.scalar(
            select(func.count(LandingPage.id)).where(LandingPage.business_id == business.id)
        ) == 1
        assert session.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.organization_id == agency.organization_id,
                AuditLog.action == "client_kit.provisioned",
            )
        ) == 1


def test_client_kit_refuses_production(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    from growthos.config import get_settings

    get_settings.cache_clear()
    try:
        assert main(["--org", "missing", str(_input_file(tmp_path))]) == 2
    finally:
        get_settings.cache_clear()
