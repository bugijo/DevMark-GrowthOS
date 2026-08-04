from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from growthos.database import get_session_factory
from growthos.domain.enums import ApprovalStatus, ProfessionalReviewDecision, Role
from growthos.models import Approval, AuditLog, ContentVersion, ProfessionalContentReview
from tests.conftest import (
    Identity,
    add_user_to_identity,
    create_identity,
    create_ready_media,
    csrf_headers,
    login,
)


@dataclass(frozen=True)
class SensitiveFlow:
    admin: Identity
    reviewer: Identity
    content: dict[str, Any]
    admin_headers: dict[str, str]


def _prepare_sensitive_content(client: TestClient, slug: str) -> SensitiveFlow:
    admin = create_identity(
        slug=slug,
        email=f"{slug}-admin@example.com",
        role=Role.AGENCY_ADMIN,
        business_name=f"Clínica {slug}",
    )
    reviewer = add_user_to_identity(
        admin,
        email=f"{slug}-reviewer@example.com",
        role=Role.CLIENT_REVIEWER,
    )
    assert admin.business_id is not None
    headers = csrf_headers(login(client, admin))
    media_id = create_ready_media(admin)
    generated = client.post(
        "/api/v1/contents/generate",
        json={
            "business_id": str(admin.business_id),
            "objective": (
                "Orientar o tutor do cão: administre o medicamento recomendado na dose de 5 mg"
            ),
            "channel": "INSTAGRAM",
            "format": "FEED",
            "media_asset_id": str(media_id),
        },
        headers=headers,
    )
    assert generated.status_code == 201, generated.text
    content = generated.json()
    version = content["current_version"]
    assert version["is_sensitive"] is True
    assert version["sensitivity_score"] >= 90
    assert "DOSAGE" in version["sensitivity_categories"]
    assert version["sensitivity_provider"] == ("contextual_rules+mock_veterinary_safety")
    assert version["sensitivity_provider_version"] != "legacy-v1"
    submitted = client.post(
        f"/api/v1/contents/{content['id']}/submit-internal",
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    sent = client.post(
        f"/api/v1/contents/{content['id']}/send-to-client",
        headers=headers,
    )
    assert sent.status_code == 200, sent.text
    return SensitiveFlow(admin, reviewer, sent.json(), headers)


def _grant_professional_review(client: TestClient, flow: SensitiveFlow) -> None:
    response = client.patch(
        f"/api/v1/members/{flow.reviewer.membership_id}",
        json={"professional_review_granted": True},
        headers=flow.admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["professional_review_granted"] is True


def _professional_decision(
    client: TestClient,
    content_id: object,
    headers: dict[str, str],
    decision: ProfessionalReviewDecision,
    justification: str,
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/contents/{content_id}/professional-reviews",
        json={"decision": decision.value, "justification": justification},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_sensitive_version_requires_grant_and_professional_approval(
    client: TestClient,
) -> None:
    flow = _prepare_sensitive_content(client, "professional-gate")
    reviewer_client = TestClient(client.app)
    reviewer_headers = csrf_headers(login(reviewer_client, flow.reviewer))
    content_id = flow.content["id"]

    common_approval = reviewer_client.post(
        f"/api/v1/contents/{content_id}/decisions/TEXT/approve",
        json={"comment": "Aprovação comum antecipada"},
        headers=reviewer_headers,
    )
    assert common_approval.status_code == 409
    assert "aprovação profissional" in common_approval.json()["detail"].lower()
    without_grant = reviewer_client.post(
        f"/api/v1/contents/{content_id}/professional-reviews",
        json={"decision": "APPROVED", "justification": "Conteúdo tecnicamente correto."},
        headers=reviewer_headers,
    )
    assert without_grant.status_code == 403

    _grant_professional_review(client, flow)
    # A mudança de concessão invalida sessões anteriores da pessoa afetada.
    assert reviewer_client.get("/api/v1/auth/me").status_code == 401
    reviewer_headers = csrf_headers(login(reviewer_client, flow.reviewer))
    reviewed = _professional_decision(
        reviewer_client,
        content_id,
        reviewer_headers,
        ProfessionalReviewDecision.APPROVED,
        "Dose apresentada somente como conteúdo fictício revisado.",
    )
    assert reviewed["status"] == "CLIENT_REVIEW"
    assert (
        reviewed["professional_reviews"][0]["content_version_id"]
        == (reviewed["current_version"]["id"])
    )

    text = reviewer_client.post(
        f"/api/v1/contents/{content_id}/decisions/TEXT/approve",
        json={"comment": "Texto aprovado"},
        headers=reviewer_headers,
    )
    assert text.status_code == 200, text.text
    image = reviewer_client.post(
        f"/api/v1/contents/{content_id}/decisions/IMAGE/approve",
        json={"comment": "Imagem aprovada"},
        headers=reviewer_headers,
    )
    assert image.status_code == 200, image.text
    assert image.json()["status"] == "APPROVED"

    with get_session_factory()() as session:
        grant_audit = session.scalar(
            select(AuditLog).where(
                AuditLog.organization_id == flow.admin.organization_id,
                AuditLog.action == "membership.professional_review_grant_changed",
            )
        )
        review_audit = session.scalar(
            select(AuditLog).where(
                AuditLog.organization_id == flow.admin.organization_id,
                AuditLog.action == "content.professional_review_approved",
            )
        )
        assert grant_audit is not None
        assert grant_audit.details["granted"] is True
        assert review_audit is not None
        assert review_audit.details["content_version_id"] == (image.json()["current_version"]["id"])
        assert "Dose apresentada" not in str(review_audit.details)


def test_legacy_unassessed_version_fails_closed_before_common_approval(
    client: TestClient,
) -> None:
    flow = _prepare_sensitive_content(client, "professional-legacy")
    current_version = flow.content["current_version"]
    assert isinstance(current_version, dict)
    version_id = UUID(str(current_version["id"]))
    with get_session_factory()() as session:
        version = session.get(ContentVersion, version_id)
        assert version is not None
        version.is_sensitive = False
        version.sensitivity_categories = []
        version.sensitivity_codes = []
        version.sensitivity_score = 0
        version.sensitivity_provider = "legacy_unassessed"
        version.sensitivity_provider_version = "legacy-v1"
        session.commit()

    reviewer_client = TestClient(client.app)
    reviewer_headers = csrf_headers(login(reviewer_client, flow.reviewer))
    blocked = reviewer_client.post(
        f"/api/v1/contents/{flow.content['id']}/decisions/TEXT/approve",
        json={"comment": "Não deve liberar versão sem classificação"},
        headers=reviewer_headers,
    )
    assert blocked.status_code == 409, blocked.text
    assert "versão legada" in blocked.json()["detail"].lower()


def test_new_sensitive_version_requires_a_new_professional_review(
    client: TestClient,
) -> None:
    flow = _prepare_sensitive_content(client, "professional-version")
    _grant_professional_review(client, flow)
    reviewer_client = TestClient(client.app)
    reviewer_headers = csrf_headers(login(reviewer_client, flow.reviewer))
    content_id = flow.content["id"]
    first = _professional_decision(
        reviewer_client,
        content_id,
        reviewer_headers,
        ProfessionalReviewDecision.APPROVED,
        "Primeira versão revisada pelo responsável.",
    )
    first_version_id = first["current_version"]["id"]
    requested = reviewer_client.post(
        f"/api/v1/contents/{content_id}/decisions/TEXT/request-changes",
        json={"comment": "Ajustar a redação antes da aprovação comum."},
        headers=reviewer_headers,
    )
    assert requested.status_code == 200, requested.text

    revised = client.post(
        f"/api/v1/contents/{content_id}/revisions",
        json={
            "title": "Orientação veterinária revisada",
            "caption": ("Para o seu cão, administre o medicamento recomendado na dose de 5 mg."),
            "cta": "Consulte o responsável técnico.",
        },
        headers=flow.admin_headers,
    )
    assert revised.status_code == 200, revised.text
    second_version_id = revised.json()["current_version"]["id"]
    assert second_version_id != first_version_id
    assert revised.json()["current_version"]["is_sensitive"] is True
    assert (
        client.post(
            f"/api/v1/contents/{content_id}/submit-internal", headers=flow.admin_headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/contents/{content_id}/send-to-client", headers=flow.admin_headers
        ).status_code
        == 200
    )

    stale_review_cannot_clear = reviewer_client.post(
        f"/api/v1/contents/{content_id}/decisions/TEXT/approve",
        json={},
        headers=reviewer_headers,
    )
    assert stale_review_cannot_clear.status_code == 409
    second = _professional_decision(
        reviewer_client,
        content_id,
        reviewer_headers,
        ProfessionalReviewDecision.APPROVED,
        "Segunda versão revisada de forma independente.",
    )
    history = reviewer_client.get(f"/api/v1/contents/{content_id}/professional-reviews")
    assert history.status_code == 200, history.text
    assert [row["content_version_id"] for row in history.json()] == [
        first_version_id,
        second_version_id,
    ]
    assert len(second["professional_reviews"]) == 2


def test_professional_change_request_is_append_only_scoped_and_audited(
    client: TestClient,
) -> None:
    flow = _prepare_sensitive_content(client, "professional-changes")
    owner = add_user_to_identity(
        flow.admin,
        email="professional-owner@example.com",
        role=Role.CLIENT_OWNER,
    )
    owner_client = TestClient(client.app)
    owner_headers = csrf_headers(login(owner_client, owner))
    forbidden_grant = owner_client.patch(
        f"/api/v1/members/{flow.reviewer.membership_id}",
        json={"professional_review_granted": True},
        headers=owner_headers,
    )
    assert forbidden_grant.status_code == 403

    _grant_professional_review(client, flow)
    reviewer_client = TestClient(client.app)
    reviewer_headers = csrf_headers(login(reviewer_client, flow.reviewer))

    other_client = TestClient(client.app)
    other = _prepare_sensitive_content(other_client, "professional-other")
    cross_tenant = reviewer_client.post(
        f"/api/v1/contents/{other.content['id']}/professional-reviews",
        json={"decision": "APPROVED", "justification": "Não deve acessar."},
        headers=reviewer_headers,
    )
    assert cross_tenant.status_code == 404

    content_id = flow.content["id"]
    changed = _professional_decision(
        reviewer_client,
        content_id,
        reviewer_headers,
        ProfessionalReviewDecision.CHANGES_REQUESTED,
        "Remover a dosagem e orientar avaliação individual pelo veterinário.",
    )
    assert changed["status"] == "CHANGES_REQUESTED"
    assert changed["change_request_comment"].startswith("Remover a dosagem")
    assert {approval["status"] for approval in changed["approvals"]} == {"CANCELLED"}

    duplicate = reviewer_client.post(
        f"/api/v1/contents/{content_id}/professional-reviews",
        json={"decision": "APPROVED", "justification": "Tentativa de sobrescrever."},
        headers=reviewer_headers,
    )
    assert duplicate.status_code == 409
    with get_session_factory()() as session:
        reviews = session.scalars(
            select(ProfessionalContentReview).where(
                ProfessionalContentReview.organization_id == flow.admin.organization_id,
                ProfessionalContentReview.content_item_id == UUID(str(content_id)),
            )
        ).all()
        approvals = session.scalars(
            select(Approval).where(
                Approval.organization_id == flow.admin.organization_id,
                Approval.content_item_id == UUID(str(content_id)),
            )
        ).all()
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.organization_id == flow.admin.organization_id,
                AuditLog.action == "content.professional_changes_requested",
            )
        )
        assert len(reviews) == 1
        assert reviews[0].decision == ProfessionalReviewDecision.CHANGES_REQUESTED
        assert all(approval.status == ApprovalStatus.CANCELLED for approval in approvals)
        assert audit is not None
        assert audit.details["justification_present"] is True
        assert "Remover a dosagem" not in str(audit.details)


def test_visual_revision_reclassifies_without_mutating_previous_snapshot(
    client: TestClient,
) -> None:
    admin = create_identity(
        slug="professional-visual",
        email="professional-visual-admin@example.com",
        role=Role.AGENCY_ADMIN,
        business_name="Clínica Visual",
    )
    reviewer = add_user_to_identity(
        admin,
        email="professional-visual-reviewer@example.com",
        role=Role.CLIENT_REVIEWER,
    )
    assert admin.business_id is not None
    admin_headers = csrf_headers(login(client, admin))
    generated = client.post(
        "/api/v1/contents/generate",
        json={
            "business_id": str(admin.business_id),
            "objective": "Apresentar os espaços acolhedores da clínica para tutores de pets",
            "channel": "INSTAGRAM",
            "format": "FEED",
            "media_asset_id": str(create_ready_media(admin)),
        },
        headers=admin_headers,
    )
    assert generated.status_code == 201, generated.text
    original_version = generated.json()["current_version"]
    assert original_version["is_sensitive"] is False
    content_id = generated.json()["id"]
    assert (
        client.post(
            f"/api/v1/contents/{content_id}/submit-internal", headers=admin_headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/contents/{content_id}/send-to-client", headers=admin_headers
        ).status_code
        == 200
    )

    reviewer_client = TestClient(client.app)
    reviewer_headers = csrf_headers(login(reviewer_client, reviewer))
    requested = reviewer_client.post(
        f"/api/v1/contents/{content_id}/decisions/IMAGE/request-changes",
        json={"comment": "Recriar a imagem."},
        headers=reviewer_headers,
    )
    assert requested.status_code == 200, requested.text
    revised = client.post(
        f"/api/v1/contents/{content_id}/visual-revisions",
        json={
            "visual_prompt": (
                "Cena veterinária para pet: administre medicamento recomendado na dose de 5 mg"
            )
        },
        headers=admin_headers,
    )
    assert revised.status_code == 200, revised.text
    current = revised.json()["current_version"]
    assert current["id"] != original_version["id"]
    assert current["is_sensitive"] is True
    assert "VET_DOSAGE_INSTRUCTION" in current["sensitivity_codes"]

    with get_session_factory()() as session:
        original = session.get(ContentVersion, UUID(original_version["id"]))
        assert original is not None
        assert original.is_sensitive is False
        assert original.sensitivity_codes == []
