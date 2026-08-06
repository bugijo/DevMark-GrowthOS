from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from growthos.database import get_session_factory
from growthos.domain.enums import Role
from growthos.models import (
    AIGeneration,
    AIGenerationAlternative,
    AIGenerationFeedback,
    AIUsageDaily,
    AuditLog,
)
from tests.conftest import Identity, add_user_to_identity, create_identity, csrf_headers, login


def _generate(
    client: TestClient, identity: Identity, csrf: str, instruction: str
) -> dict[str, object]:
    business_id = identity.business_id
    response = client.post(
        f"/api/v1/businesses/{business_id}/ai/generations",
        headers=csrf_headers(csrf),
        json={"task": "CONTENT_IDEAS", "instruction": instruction, "alternatives": 3},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_privacy_export_contains_subject_ai_data_without_other_tenant(client: TestClient) -> None:
    first = create_identity(
        slug="ai-export-first",
        email="ai-export-first@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica A",
    )
    second = create_identity(
        slug="ai-export-second",
        email="ai-export-second@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica B",
    )
    first_csrf = login(client, first)
    first_generation = _generate(client, first, first_csrf, "Instrução exclusiva do titular A")
    feedback = client.post(
        f"/api/v1/ai/generations/{first_generation['id']}/feedback",
        headers=csrf_headers(first_csrf),
        json={"rating": "HELPFUL", "comment": "Feedback pessoal do titular A"},
    )
    assert feedback.status_code == 204
    second_csrf = login(client, second)
    _generate(client, second, second_csrf, "Instrução que pertence somente ao tenant B")

    login(client, first)
    response = client.get("/api/v1/privacy/export")
    assert response.status_code == 200
    body = response.json()
    assert body["format_version"] == "1.1"
    assert len(body["ai_generations"]) == 1
    exported = body["ai_generations"][0]
    assert exported["instruction"] == "Instrução exclusiva do titular A"
    assert exported["feedback"][0]["comment"] == "Feedback pessoal do titular A"
    assert len(exported["alternatives"]) == 3
    assert exported["provider"] == "mock"
    assert "tenant B" not in response.text
    assert "api_key" not in response.text.casefold()
    assert "cookie" not in response.text.casefold()


def test_deletion_anonymizes_ai_text_and_identifiers_but_preserves_aggregates(
    client: TestClient,
) -> None:
    admin = create_identity(
        slug="ai-delete-admin",
        email="ai-delete-admin@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica",
    )
    subject = add_user_to_identity(
        admin, email="ai-delete-subject@example.test", role=Role.CONTENT_EDITOR
    )
    subject_csrf = login(client, subject)
    generated = _generate(client, admin, subject_csrf, "Meu nome e dado pessoal na instrução")
    response = client.post(
        f"/api/v1/ai/generations/{generated['id']}/feedback",
        headers=csrf_headers(subject_csrf),
        json={"rating": "NOT_HELPFUL", "comment": "Meu comentário identificável"},
    )
    assert response.status_code == 204
    requested = client.post(
        "/api/v1/privacy/requests",
        headers=csrf_headers(subject_csrf),
        json={"request_type": "DELETION", "reason": "Anonimizar meus dados de IA"},
    )
    admin_csrf = login(client, admin)
    resolved = client.post(
        f"/api/v1/privacy/admin/requests/{requested.json()['id']}/resolve",
        headers=csrf_headers(admin_csrf),
        json={"decision": "COMPLETE", "notes": "Anonimização conforme política de IA."},
    )
    assert resolved.status_code == 200, resolved.text

    with get_session_factory()() as session:
        generation = session.get(AIGeneration, UUID(str(generated["id"])))
        assert generation is not None
        assert generation.requested_by_user_id is None
        assert generation.instruction == "[ANONIMIZADO POR SOLICITAÇÃO LGPD]"
        assert generation.context_snapshot == {"privacy_status": "ANONYMIZED"}
        alternatives = session.scalars(
            select(AIGenerationAlternative).where(
                AIGenerationAlternative.generation_id == generation.id
            )
        ).all()
        assert alternatives and all(
            item.payload == {"privacy_status": "ANONYMIZED"} for item in alternatives
        )
        feedback = session.scalar(
            select(AIGenerationFeedback).where(
                AIGenerationFeedback.generation_id == generation.id
            )
        )
        assert feedback is not None and feedback.user_id is None
        assert feedback.comment == "[ANONIMIZADO POR SOLICITAÇÃO LGPD]"
        usage = session.scalar(
            select(AIUsageDaily).where(AIUsageDaily.organization_id == admin.organization_id)
        )
        assert usage is not None and usage.generation_count == 1
        audit = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.organization_id == admin.organization_id,
                AuditLog.action == "privacy.request_resolved",
            )
            .order_by(AuditLog.created_at.desc())
        )
        assert audit is not None and audit.details["ai_anonymized"] == {
            "generations": 1,
            "feedback": 1,
        }


def test_ai_retention_dry_run_real_run_and_idempotency_are_tenant_scoped(
    client: TestClient,
) -> None:
    first = create_identity(
        slug="ai-retention-first",
        email="ai-retention-first@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica A",
    )
    second = create_identity(
        slug="ai-retention-second",
        email="ai-retention-second@example.test",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica B",
    )
    first_csrf = login(client, first)
    first_generation = _generate(client, first, first_csrf, "Expirar snapshot A")
    second_csrf = login(client, second)
    second_generation = _generate(client, second, second_csrf, "Preservar snapshot B")
    old = datetime.now(UTC) - timedelta(days=10)
    with get_session_factory()() as session:
        first_row = session.get(AIGeneration, UUID(str(first_generation["id"])))
        second_row = session.get(AIGeneration, UUID(str(second_generation["id"])))
        assert first_row is not None and second_row is not None
        first_row.created_at = old
        second_row.created_at = old
        session.commit()

    first_csrf = login(client, first)
    policy = client.put(
        "/api/v1/privacy/admin/retention/ai_generation_snapshots",
        headers=csrf_headers(first_csrf),
        json={
            "retention_days": 1,
            "legal_hold": False,
            "justification": "Minimizar snapshots antigos conforme política LGPD.",
        },
    )
    assert policy.status_code == 200
    dry = client.post(
        "/api/v1/privacy/admin/retention/run",
        headers=csrf_headers(first_csrf),
        json={"resource_type": "ai_generation_snapshots", "dry_run": True},
    )
    assert dry.status_code == 200 and dry.json()["affected_count"] == 1
    with get_session_factory()() as session:
        row = session.get(AIGeneration, UUID(str(first_generation["id"])))
        assert row is not None and row.context_snapshot != {"retention_status": "EXPIRED"}
    real = client.post(
        "/api/v1/privacy/admin/retention/run",
        headers=csrf_headers(first_csrf),
        json={"resource_type": "ai_generation_snapshots", "dry_run": False},
    )
    assert real.status_code == 200 and real.json()["affected_count"] == 1
    repeated = client.post(
        "/api/v1/privacy/admin/retention/run",
        headers=csrf_headers(first_csrf),
        json={"resource_type": "ai_generation_snapshots", "dry_run": False},
    )
    assert repeated.status_code == 200 and repeated.json()["affected_count"] == 0
    with get_session_factory()() as session:
        first_row = session.get(AIGeneration, UUID(str(first_generation["id"])))
        second_row = session.get(AIGeneration, UUID(str(second_generation["id"])))
        assert first_row is not None and first_row.context_snapshot == {
            "retention_status": "EXPIRED"
        }
        assert second_row is not None and second_row.context_snapshot != {
            "retention_status": "EXPIRED"
        }
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(
                    AuditLog.organization_id == first.organization_id,
                    AuditLog.action == "privacy.retention_executed",
                )
            )
            == 2
        )


def test_viewer_cannot_execute_ai_retention(client: TestClient) -> None:
    viewer = create_identity(
        slug="ai-retention-viewer",
        email="ai-retention-viewer@example.test",
        role=Role.VIEWER,
        business_name="Clínica",
    )
    csrf = login(client, viewer)
    response = client.post(
        "/api/v1/privacy/admin/retention/run",
        headers=csrf_headers(csrf),
        json={"resource_type": "ai_generation_feedback", "dry_run": True},
    )
    assert response.status_code == 403
