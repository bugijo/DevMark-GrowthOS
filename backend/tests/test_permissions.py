import pytest

from growthos.domain.enums import Role
from growthos.domain.permissions import (
    MUTATING_CAPABILITIES,
    ROLE_CAPABILITIES,
    Capability,
    capabilities_for,
    has_capability,
)


def test_matrix_covers_exactly_all_official_roles() -> None:
    assert set(ROLE_CAPABILITIES) == set(Role)
    assert all(isinstance(values, frozenset) for values in ROLE_CAPABILITIES.values())
    assert all(values <= frozenset(Capability) for values in ROLE_CAPABILITIES.values())


@pytest.mark.parametrize("capability", list(Capability))
def test_super_admin_has_every_capability_but_still_needs_explicit_scope(
    capability: Capability,
) -> None:
    assert has_capability(Role.SUPER_ADMIN, capability)


def test_agency_admin_cannot_decide_for_client() -> None:
    assert has_capability(Role.AGENCY_ADMIN, Capability.CONTENT_SEND_CLIENT)
    assert not has_capability(Role.AGENCY_ADMIN, Capability.CONTENT_DECIDE_CLIENT)
    assert not has_capability(Role.AGENCY_ADMIN, Capability.STRATEGY_DECIDE_CLIENT)


def test_specialists_receive_only_their_operational_mutations() -> None:
    assert has_capability(Role.STRATEGIST, Capability.STRATEGY_REVIEW_INTERNAL)
    assert not has_capability(Role.STRATEGIST, Capability.PRESET_MANAGE)

    assert has_capability(Role.CONTENT_EDITOR, Capability.CONTENT_EDIT_TEXT)
    assert not has_capability(Role.CONTENT_EDITOR, Capability.CONTENT_EDIT_VISUAL)
    assert not has_capability(Role.CONTENT_EDITOR, Capability.CONTENT_DECIDE_CLIENT)

    assert has_capability(Role.DESIGNER, Capability.CONTENT_EDIT_VISUAL)
    assert has_capability(Role.DESIGNER, Capability.PRESET_MANAGE)
    assert not has_capability(Role.DESIGNER, Capability.CONTENT_EDIT_TEXT)


def test_client_owner_can_manage_only_client_memberships() -> None:
    assert has_capability(Role.CLIENT_OWNER, Capability.CLIENT_MEMBERSHIP_MANAGE)
    assert has_capability(Role.CLIENT_OWNER, Capability.CLIENT_INVITATION_MANAGE)
    assert not has_capability(Role.CLIENT_OWNER, Capability.MEMBERSHIP_MANAGE)
    assert not has_capability(Role.CLIENT_REVIEWER, Capability.CLIENT_MEMBERSHIP_MANAGE)


@pytest.mark.parametrize("role", [Role.CLIENT_OWNER, Role.CLIENT_REVIEWER])
def test_client_decision_roles_can_decide_but_not_edit_drafts(role: Role) -> None:
    assert has_capability(role, Capability.CONTENT_DECIDE_CLIENT)
    assert has_capability(role, Capability.STRATEGY_DECIDE_CLIENT)
    assert not has_capability(role, Capability.CONTENT_EDIT_TEXT)
    assert not has_capability(role, Capability.CONTENT_EDIT_VISUAL)


def test_viewer_has_no_mutating_capability() -> None:
    assert capabilities_for(Role.VIEWER).isdisjoint(MUTATING_CAPABILITIES)
    assert has_capability(Role.VIEWER, Capability.CONTENT_VIEW)
    assert not has_capability(Role.VIEWER, Capability.CONTENT_COMMENT)


def test_capability_sets_are_immutable() -> None:
    with pytest.raises(AttributeError):
        capabilities_for(Role.VIEWER).add(Capability.CONTENT_COMMENT)  # type: ignore[attr-defined]
    with pytest.raises(TypeError):
        ROLE_CAPABILITIES[Role.VIEWER] = frozenset()  # type: ignore[index]
