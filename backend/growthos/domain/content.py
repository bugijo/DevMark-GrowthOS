from growthos.domain.enums import ContentStatus


class InvalidContentTransition(ValueError):
    pass


ALLOWED_TRANSITIONS: dict[ContentStatus, frozenset[ContentStatus]] = {
    ContentStatus.DRAFT: frozenset(
        {ContentStatus.INTERNAL_REVIEW, ContentStatus.FAILED, ContentStatus.ARCHIVED}
    ),
    ContentStatus.INTERNAL_REVIEW: frozenset(
        {ContentStatus.CLIENT_REVIEW, ContentStatus.CHANGES_REQUESTED, ContentStatus.ARCHIVED}
    ),
    ContentStatus.CLIENT_REVIEW: frozenset(
        {ContentStatus.APPROVED, ContentStatus.CHANGES_REQUESTED, ContentStatus.ARCHIVED}
    ),
    ContentStatus.CHANGES_REQUESTED: frozenset({ContentStatus.DRAFT, ContentStatus.ARCHIVED}),
    ContentStatus.APPROVED: frozenset({ContentStatus.SCHEDULED, ContentStatus.ARCHIVED}),
    ContentStatus.SCHEDULED: frozenset(
        {ContentStatus.APPROVED, ContentStatus.PUBLISHED, ContentStatus.FAILED}
    ),
    ContentStatus.PUBLISHED: frozenset({ContentStatus.ARCHIVED}),
    ContentStatus.FAILED: frozenset(
        {ContentStatus.DRAFT, ContentStatus.SCHEDULED, ContentStatus.ARCHIVED}
    ),
    ContentStatus.ARCHIVED: frozenset(),
}


def validate_transition(current: ContentStatus, target: ContentStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidContentTransition(f"Transição inválida: {current} -> {target}")
