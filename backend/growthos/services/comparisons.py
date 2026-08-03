from collections import defaultdict
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from growthos.dependencies import AuthContext, get_scoped_business
from growthos.domain.enums import (
    ApprovalComponent,
    ApprovalStage,
    ApprovalStatus,
    Role,
)
from growthos.models.catalog import ContentVersionMedia
from growthos.models.content import Approval, ContentItem, ContentVersion
from growthos.models.identity import Membership, User
from growthos.models.operations import AuditLog
from growthos.models.planning import ContentStrategy, StrategyVersion
from growthos.schemas_comparisons import (
    ComparisonActorRead,
    ContentTextFieldsRead,
    ContentVersionComparisonRead,
    ContentVersionComparisonSideRead,
    ContentVersionHistoryRead,
    ContentVisualFieldsRead,
    StrategyFieldsRead,
    StrategyVersionComparisonRead,
    StrategyVersionComparisonSideRead,
    StrategyVersionHistoryRead,
    VersionDecisionRead,
    VersionSummaryRead,
)
from growthos.services.content.read_models import get_content

_CONTENT_APPROVAL_COMPONENTS = frozenset({ApprovalComponent.TEXT, ApprovalComponent.IMAGE})
_SAFE_PRESET_FIELDS = (
    "id",
    "version",
    "name",
    "objective",
    "format",
    "aspect_ratio",
    "creation_mode",
    "color_palette",
    "fonts",
    "logo_media_asset_id",
    "logo_position",
    "logo_scale_percent",
    "safe_margins",
    "background_style",
    "photographic_style",
    "realism_level",
    "lighting",
    "composition",
    "max_text_characters",
    "text_rules",
    "allowed_elements",
    "forbidden_elements",
    "visual_signature",
    "default_cta",
)
_SAFE_CATALOG_FIELDS = ("id", "name", "description", "category")
_SAFE_PILLAR_FIELDS = ("name", "title", "description", "objective")


def _actor_names(
    session: Session,
    organization_id: UUID,
    business_id: UUID,
    user_ids: Iterable[UUID | None],
) -> dict[UUID, str]:
    scoped_ids = {user_id for user_id in user_ids if user_id is not None}
    if not scoped_ids:
        return {}
    rows = session.execute(
        select(User.id, User.name)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.organization_id == organization_id,
            or_(
                Membership.business_id.is_(None),
                Membership.business_id == business_id,
            ),
            User.id.in_(scoped_ids),
        )
        .order_by(User.id)
    ).all()
    return {user_id: name for user_id, name in rows}


def _actor(user_id: UUID | None, names: dict[UUID, str]) -> ComparisonActorRead | None:
    if user_id is None:
        return None
    return ComparisonActorRead(name=names.get(user_id, "Usuário indisponível"))


def _safe_mapping(
    source: dict[str, Any] | None,
    allowed_fields: tuple[str, ...],
) -> dict[str, Any]:
    if not source:
        return {}
    return {field: source[field] for field in allowed_fields if field in source}


def _safe_catalog_snapshots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = [_safe_mapping(row, _SAFE_CATALOG_FIELDS) for row in rows]
    return sorted(
        sanitized,
        key=lambda row: (str(row.get("name", "")), str(row.get("id", ""))),
    )


def _safe_pillars(rows: list[str | dict[str, Any]]) -> list[str | dict[str, Any]]:
    return [
        _safe_mapping(row, _SAFE_PILLAR_FIELDS) if isinstance(row, dict) else row for row in rows
    ]


def _content_versions(
    session: Session,
    content: ContentItem,
    version_ids: set[UUID] | None = None,
) -> list[ContentVersion]:
    query = select(ContentVersion).where(
        ContentVersion.organization_id == content.organization_id,
        ContentVersion.business_id == content.business_id,
        ContentVersion.content_item_id == content.id,
    )
    if version_ids is not None:
        query = query.where(ContentVersion.id.in_(version_ids))
    return list(
        session.scalars(query.order_by(ContentVersion.version_number, ContentVersion.id)).all()
    )


def _ensure_content_current_version(session: Session, content: ContentItem) -> UUID:
    if content.current_version_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Conteúdo sem versão atual")
    current_version_id = session.scalar(
        select(ContentVersion.id).where(
            ContentVersion.id == content.current_version_id,
            ContentVersion.organization_id == content.organization_id,
            ContentVersion.business_id == content.business_id,
            ContentVersion.content_item_id == content.id,
        )
    )
    if current_version_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Versão atual inconsistente")
    return current_version_id


def _content_media(
    session: Session,
    content: ContentItem,
    version_ids: set[UUID],
) -> dict[UUID, list[UUID]]:
    result: dict[UUID, list[UUID]] = defaultdict(list)
    if not version_ids:
        return result
    rows = session.execute(
        select(
            ContentVersionMedia.content_version_id,
            ContentVersionMedia.media_asset_id,
        )
        .where(
            ContentVersionMedia.organization_id == content.organization_id,
            ContentVersionMedia.business_id == content.business_id,
            ContentVersionMedia.content_version_id.in_(version_ids),
        )
        .order_by(
            ContentVersionMedia.content_version_id,
            ContentVersionMedia.sort_order,
            ContentVersionMedia.created_at,
            ContentVersionMedia.id,
        )
    ).all()
    for version_id, media_asset_id in rows:
        result[version_id].append(media_asset_id)
    return result


def _content_approvals(
    session: Session,
    content: ContentItem,
    version_ids: set[UUID],
) -> dict[UUID, list[Approval]]:
    result: dict[UUID, list[Approval]] = defaultdict(list)
    if not version_ids:
        return result
    approvals = session.scalars(
        select(Approval)
        .where(
            Approval.organization_id == content.organization_id,
            Approval.business_id == content.business_id,
            Approval.content_item_id == content.id,
            Approval.content_version_id.in_(version_ids),
            Approval.stage == ApprovalStage.CLIENT,
        )
        .order_by(Approval.content_version_id, Approval.component, Approval.id)
    ).all()
    for approval in approvals:
        result[approval.content_version_id].append(approval)
    return result


def _is_content_version_approved(approvals: list[Approval]) -> bool:
    approved = {
        approval.component for approval in approvals if approval.status == ApprovalStatus.APPROVED
    }
    return approved == _CONTENT_APPROVAL_COMPONENTS


def _content_decisions(
    approvals: list[Approval],
    actor_names: dict[UUID, str],
) -> list[VersionDecisionRead]:
    return [
        VersionDecisionRead(
            status=approval.status.value,
            component=approval.component.value,
            comment=approval.decision_comment,
            decided_at=approval.decided_at,
            decided_by=_actor(approval.decided_by_user_id, actor_names),
        )
        for approval in approvals
    ]


def _content_summary(
    content: ContentItem,
    version: ContentVersion,
    approvals: list[Approval],
    actor_names: dict[UUID, str],
) -> VersionSummaryRead:
    author = _actor(version.created_by_user_id, actor_names)
    assert author is not None
    return VersionSummaryRead(
        id=version.id,
        version_number=version.version_number,
        created_at=version.created_at,
        author=author,
        is_current=content.current_version_id == version.id,
        is_approved=_is_content_version_approved(approvals),
        decisions=_content_decisions(approvals, actor_names),
    )


def _content_side(
    content: ContentItem,
    version: ContentVersion,
    media_asset_ids: list[UUID],
    approvals: list[Approval],
    actor_names: dict[UUID, str],
) -> ContentVersionComparisonSideRead:
    summary = _content_summary(content, version, approvals, actor_names)
    return ContentVersionComparisonSideRead(
        **summary.model_dump(),
        text=ContentTextFieldsRead(
            title=version.title,
            caption=version.caption,
            objective=version.objective,
            audience=version.audience,
            cta=version.cta,
            script=version.script,
        ),
        visual=ContentVisualFieldsRead(
            channel=version.channel,
            format=version.format,
            preset=_safe_mapping(version.visual_preset_snapshot, _SAFE_PRESET_FIELDS),
            media_asset_ids=media_asset_ids,
        ),
    )


def content_history(
    session: Session,
    context: AuthContext,
    content_id: UUID,
) -> ContentVersionHistoryRead:
    content = get_content(session, context, content_id)
    current_version_id = _ensure_content_current_version(session, content)
    versions = _content_versions(session, content)
    version_ids = {version.id for version in versions}
    approvals = _content_approvals(session, content, version_ids)
    names = _actor_names(
        session,
        content.organization_id,
        content.business_id,
        [
            *(version.created_by_user_id for version in versions),
            *(
                approval.decided_by_user_id
                for version_approvals in approvals.values()
                for approval in version_approvals
            ),
        ],
    )
    return ContentVersionHistoryRead(
        content_id=content.id,
        business_id=content.business_id,
        current_version_id=current_version_id,
        versions=[
            _content_summary(content, version, approvals[version.id], names) for version in versions
        ],
    )


def compare_content_versions(
    session: Session,
    context: AuthContext,
    content_id: UUID,
    base_version_id: UUID,
    target_version_id: UUID,
) -> ContentVersionComparisonRead:
    if base_version_id == target_version_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Selecione duas versões diferentes",
        )
    content = get_content(session, context, content_id)
    _ensure_content_current_version(session, content)
    requested_ids = {base_version_id, target_version_id}
    versions = _content_versions(session, content, requested_ids)
    versions_by_id = {version.id: version for version in versions}
    if len(versions_by_id) != 2:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versão de conteúdo não encontrada")
    approvals = _content_approvals(session, content, requested_ids)
    media = _content_media(session, content, requested_ids)
    names = _actor_names(
        session,
        content.organization_id,
        content.business_id,
        [
            *(version.created_by_user_id for version in versions),
            *(
                approval.decided_by_user_id
                for version_approvals in approvals.values()
                for approval in version_approvals
            ),
        ],
    )
    base = _content_side(
        content,
        versions_by_id[base_version_id],
        media[base_version_id],
        approvals[base_version_id],
        names,
    )
    target = _content_side(
        content,
        versions_by_id[target_version_id],
        media[target_version_id],
        approvals[target_version_id],
        names,
    )
    fields = (
        ("text.title", base.text.title, target.text.title),
        ("text.caption", base.text.caption, target.text.caption),
        ("text.objective", base.text.objective, target.text.objective),
        ("text.audience", base.text.audience, target.text.audience),
        ("text.cta", base.text.cta, target.text.cta),
        ("text.script", base.text.script, target.text.script),
        ("visual.channel", base.visual.channel, target.visual.channel),
        ("visual.format", base.visual.format, target.visual.format),
        ("visual.preset", base.visual.preset, target.visual.preset),
        (
            "visual.media_asset_ids",
            base.visual.media_asset_ids,
            target.visual.media_asset_ids,
        ),
    )
    return ContentVersionComparisonRead(
        content_id=content.id,
        business_id=content.business_id,
        base=base,
        target=target,
        changed_fields=[name for name, old, new in fields if old != new],
    )


def _get_strategy(
    session: Session,
    context: AuthContext,
    strategy_id: UUID,
) -> ContentStrategy:
    query = select(ContentStrategy).where(
        ContentStrategy.id == strategy_id,
        ContentStrategy.organization_id == context.organization.id,
        ContentStrategy.archived_at.is_(None),
    )
    if context.membership.role in {Role.CLIENT_OWNER, Role.CLIENT_REVIEWER}:
        query = query.where(ContentStrategy.status.in_(["CLIENT_REVIEW", "APPROVED"]))
    elif context.membership.role == Role.VIEWER:
        query = query.where(ContentStrategy.status == "APPROVED")
    strategy = session.scalar(query)
    if strategy is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estratégia não encontrada")
    get_scoped_business(session, context, strategy.business_id)
    return strategy


def _strategy_versions(
    session: Session,
    strategy: ContentStrategy,
    version_ids: set[UUID] | None = None,
) -> list[StrategyVersion]:
    query = select(StrategyVersion).where(
        StrategyVersion.organization_id == strategy.organization_id,
        StrategyVersion.business_id == strategy.business_id,
        StrategyVersion.content_strategy_id == strategy.id,
    )
    if version_ids is not None:
        query = query.where(StrategyVersion.id.in_(version_ids))
    return list(
        session.scalars(query.order_by(StrategyVersion.version_number, StrategyVersion.id)).all()
    )


def _ensure_strategy_version_links(
    session: Session,
    strategy: ContentStrategy,
) -> UUID:
    if strategy.current_version_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Estratégia sem versão atual")
    linked_ids = {strategy.current_version_id}
    if strategy.approved_version_id is not None:
        linked_ids.add(strategy.approved_version_id)
    found_ids = set(
        session.scalars(
            select(StrategyVersion.id).where(
                StrategyVersion.id.in_(linked_ids),
                StrategyVersion.organization_id == strategy.organization_id,
                StrategyVersion.business_id == strategy.business_id,
                StrategyVersion.content_strategy_id == strategy.id,
            )
        ).all()
    )
    if found_ids != linked_ids:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Vínculo de versão da estratégia inconsistente"
        )
    return strategy.current_version_id


def _strategy_audits(
    session: Session,
    strategy: ContentStrategy,
) -> dict[UUID, list[AuditLog]]:
    result: dict[UUID, list[AuditLog]] = defaultdict(list)
    rows = session.scalars(
        select(AuditLog)
        .where(
            AuditLog.organization_id == strategy.organization_id,
            AuditLog.business_id == strategy.business_id,
            AuditLog.resource_type == "content_strategy",
            AuditLog.resource_id == strategy.id,
            AuditLog.action.in_(["strategy.approved_by_client", "strategy.changes_requested"]),
        )
        .order_by(AuditLog.created_at, AuditLog.id)
    ).all()
    for audit in rows:
        raw_version_id = audit.details.get("version_id")
        try:
            version_id = UUID(str(raw_version_id))
        except (TypeError, ValueError):
            continue
        result[version_id].append(audit)
    return result


def _strategy_decisions(
    strategy: ContentStrategy,
    version: StrategyVersion,
    audits: list[AuditLog],
    actor_names: dict[UUID, str],
) -> list[VersionDecisionRead]:
    decisions: list[VersionDecisionRead] = []
    last_audit = audits[-1] if audits else None
    for audit in audits:
        is_latest_persisted_decision = (
            audit is last_audit
            and strategy.decided_at is not None
            and strategy.decided_by_user_id == audit.actor_user_id
            and (
                strategy.current_version_id == version.id
                or strategy.approved_version_id == version.id
            )
        )
        decisions.append(
            VersionDecisionRead(
                status=(
                    "APPROVED"
                    if audit.action == "strategy.approved_by_client"
                    else "CHANGES_REQUESTED"
                ),
                comment=(strategy.decision_comment if is_latest_persisted_decision else None),
                decided_at=(
                    strategy.decided_at if is_latest_persisted_decision else audit.created_at
                ),
                decided_by=_actor(audit.actor_user_id, actor_names),
            )
        )
    return decisions


def _strategy_summary(
    strategy: ContentStrategy,
    version: StrategyVersion,
    audits: list[AuditLog],
    actor_names: dict[UUID, str],
) -> VersionSummaryRead:
    author = _actor(version.created_by_user_id, actor_names)
    assert author is not None
    return VersionSummaryRead(
        id=version.id,
        version_number=version.version_number,
        created_at=version.created_at,
        author=author,
        is_current=strategy.current_version_id == version.id,
        is_approved=strategy.approved_version_id == version.id,
        decisions=_strategy_decisions(strategy, version, audits, actor_names),
    )


def _strategy_side(
    strategy: ContentStrategy,
    version: StrategyVersion,
    audits: list[AuditLog],
    actor_names: dict[UUID, str],
) -> StrategyVersionComparisonSideRead:
    summary = _strategy_summary(strategy, version, audits, actor_names)
    return StrategyVersionComparisonSideRead(
        **summary.model_dump(),
        strategy=StrategyFieldsRead(
            objective=version.objective,
            positioning=version.positioning,
            funnel=list(version.funnel),
            channels=list(version.channels),
            pillars=_safe_pillars(version.pillars),
            planned_indicators=list(version.planned_indicators),
            services=_safe_catalog_snapshots(version.service_snapshots),
            audiences=_safe_catalog_snapshots(version.audience_snapshots),
            marketing_objectives=_safe_catalog_snapshots(version.objective_snapshots),
        ),
    )


def strategy_history(
    session: Session,
    context: AuthContext,
    strategy_id: UUID,
) -> StrategyVersionHistoryRead:
    strategy = _get_strategy(session, context, strategy_id)
    current_version_id = _ensure_strategy_version_links(session, strategy)
    versions = _strategy_versions(session, strategy)
    audits = _strategy_audits(session, strategy)
    names = _actor_names(
        session,
        strategy.organization_id,
        strategy.business_id,
        [
            *(version.created_by_user_id for version in versions),
            *(
                audit.actor_user_id
                for version_audits in audits.values()
                for audit in version_audits
            ),
        ],
    )
    return StrategyVersionHistoryRead(
        strategy_id=strategy.id,
        business_id=strategy.business_id,
        current_version_id=current_version_id,
        approved_version_id=strategy.approved_version_id,
        versions=[
            _strategy_summary(strategy, version, audits[version.id], names) for version in versions
        ],
    )


def compare_strategy_versions(
    session: Session,
    context: AuthContext,
    strategy_id: UUID,
    base_version_id: UUID,
    target_version_id: UUID,
) -> StrategyVersionComparisonRead:
    if base_version_id == target_version_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Selecione duas versões diferentes",
        )
    strategy = _get_strategy(session, context, strategy_id)
    _ensure_strategy_version_links(session, strategy)
    requested_ids = {base_version_id, target_version_id}
    versions = _strategy_versions(session, strategy, requested_ids)
    versions_by_id = {version.id: version for version in versions}
    if len(versions_by_id) != 2:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versão de estratégia não encontrada")
    audits = _strategy_audits(session, strategy)
    names = _actor_names(
        session,
        strategy.organization_id,
        strategy.business_id,
        [
            *(version.created_by_user_id for version in versions),
            *(
                audit.actor_user_id
                for version_audits in audits.values()
                for audit in version_audits
            ),
        ],
    )
    base = _strategy_side(
        strategy,
        versions_by_id[base_version_id],
        audits[base_version_id],
        names,
    )
    target = _strategy_side(
        strategy,
        versions_by_id[target_version_id],
        audits[target_version_id],
        names,
    )
    fields = (
        ("strategy.objective", base.strategy.objective, target.strategy.objective),
        ("strategy.positioning", base.strategy.positioning, target.strategy.positioning),
        ("strategy.funnel", base.strategy.funnel, target.strategy.funnel),
        ("strategy.channels", base.strategy.channels, target.strategy.channels),
        ("strategy.pillars", base.strategy.pillars, target.strategy.pillars),
        (
            "strategy.planned_indicators",
            base.strategy.planned_indicators,
            target.strategy.planned_indicators,
        ),
        ("strategy.services", base.strategy.services, target.strategy.services),
        ("strategy.audiences", base.strategy.audiences, target.strategy.audiences),
        (
            "strategy.marketing_objectives",
            base.strategy.marketing_objectives,
            target.strategy.marketing_objectives,
        ),
    )
    return StrategyVersionComparisonRead(
        strategy_id=strategy.id,
        business_id=strategy.business_id,
        base=base,
        target=target,
        changed_fields=[name for name, old, new in fields if old != new],
    )
