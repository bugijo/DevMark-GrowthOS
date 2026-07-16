"""Matriz central de capacidades da versão 1.0.

Papéis concedem capacidades somente depois que organização, empresa e recurso
foram resolvidos no contexto autenticado. Este módulo deliberadamente não importa
FastAPI, SQLAlchemy ou modelos de persistência.
"""

from enum import StrEnum
from types import MappingProxyType
from typing import Final

from growthos.domain.enums import Role


class Capability(StrEnum):
    ORGANIZATION_VIEW = "organization.view"
    ORGANIZATION_MANAGE = "organization.manage"

    MEMBERSHIP_VIEW = "membership.view"
    MEMBERSHIP_MANAGE = "membership.manage"
    CLIENT_MEMBERSHIP_MANAGE = "membership.manage_client"
    INVITATION_MANAGE = "invitation.manage"
    CLIENT_INVITATION_MANAGE = "invitation.manage_client"

    BUSINESS_VIEW = "business.view"
    BUSINESS_MANAGE = "business.manage"

    BRAND_VIEW = "brand.view"
    BRAND_MANAGE = "brand.manage"
    BRAND_VISUAL_MANAGE = "brand.manage_visual"
    SERVICE_MANAGE = "service.manage"
    AUDIENCE_MANAGE = "audience.manage"
    OBJECTIVE_MANAGE = "objective.manage"

    STRATEGY_VIEW = "strategy.view"
    STRATEGY_MANAGE = "strategy.manage"
    STRATEGY_REVIEW_INTERNAL = "strategy.review_internal"
    STRATEGY_DECIDE_CLIENT = "strategy.decide_client"

    CALENDAR_VIEW = "calendar.view"
    CALENDAR_MANAGE = "calendar.manage"

    PRESET_VIEW = "preset.view"
    PRESET_MANAGE = "preset.manage"
    VISUAL_PROMPT_GENERATE = "visual_prompt.generate"
    MEDIA_VIEW = "media.view"
    MEDIA_UPLOAD = "media.upload"
    MEDIA_MANAGE = "media.manage"

    CONTENT_VIEW = "content.view"
    CONTENT_CREATE = "content.create"
    CONTENT_EDIT_TEXT = "content.edit_text"
    CONTENT_EDIT_VISUAL = "content.edit_visual"
    CONTENT_SUBMIT_INTERNAL = "content.submit_internal"
    CONTENT_REVIEW_INTERNAL = "content.review_internal"
    CONTENT_SEND_CLIENT = "content.send_client"
    CONTENT_DECIDE_CLIENT = "content.decide_client"
    CONTENT_COMMENT = "content.comment"

    NOTIFICATION_VIEW_OWN = "notification.view_own"
    NOTIFICATION_UPDATE_OWN = "notification.update_own"
    PUBLICATION_RECORD = "publication.record"
    REPORT_VIEW = "report.view"

    PROVIDER_CONFIG_VIEW = "provider_config.view"
    PROVIDER_CONFIG_MANAGE = "provider_config.manage"
    AUDIT_VIEW_ORGANIZATION = "audit.view_organization"
    AUDIT_VIEW_SCOPED = "audit.view_scoped"


READ_ONLY_CAPABILITIES: Final[frozenset[Capability]] = frozenset(
    {
        Capability.ORGANIZATION_VIEW,
        Capability.MEMBERSHIP_VIEW,
        Capability.BUSINESS_VIEW,
        Capability.BRAND_VIEW,
        Capability.STRATEGY_VIEW,
        Capability.CALENDAR_VIEW,
        Capability.PRESET_VIEW,
        Capability.MEDIA_VIEW,
        Capability.CONTENT_VIEW,
        Capability.NOTIFICATION_VIEW_OWN,
        Capability.REPORT_VIEW,
        Capability.PROVIDER_CONFIG_VIEW,
        Capability.AUDIT_VIEW_ORGANIZATION,
        Capability.AUDIT_VIEW_SCOPED,
    }
)

MUTATING_CAPABILITIES: Final[frozenset[Capability]] = frozenset(Capability).difference(
    READ_ONLY_CAPABILITIES
)

_ALL_CAPABILITIES = frozenset(Capability)

_ROLE_CAPABILITIES: dict[Role, frozenset[Capability]] = {
    # A utilização entre tenants continua exigindo um caminho explícito de
    # suporte, justificativa e auditoria. A capacidade sozinha não cria escopo.
    Role.SUPER_ADMIN: _ALL_CAPABILITIES,
    Role.AGENCY_ADMIN: frozenset(
        {
            Capability.ORGANIZATION_VIEW,
            Capability.ORGANIZATION_MANAGE,
            Capability.MEMBERSHIP_VIEW,
            Capability.MEMBERSHIP_MANAGE,
            Capability.INVITATION_MANAGE,
            Capability.BUSINESS_VIEW,
            Capability.BUSINESS_MANAGE,
            Capability.BRAND_VIEW,
            Capability.BRAND_MANAGE,
            Capability.BRAND_VISUAL_MANAGE,
            Capability.SERVICE_MANAGE,
            Capability.AUDIENCE_MANAGE,
            Capability.OBJECTIVE_MANAGE,
            Capability.STRATEGY_VIEW,
            Capability.STRATEGY_MANAGE,
            Capability.STRATEGY_REVIEW_INTERNAL,
            Capability.CALENDAR_VIEW,
            Capability.CALENDAR_MANAGE,
            Capability.PRESET_VIEW,
            Capability.PRESET_MANAGE,
            Capability.VISUAL_PROMPT_GENERATE,
            Capability.MEDIA_VIEW,
            Capability.MEDIA_UPLOAD,
            Capability.MEDIA_MANAGE,
            Capability.CONTENT_VIEW,
            Capability.CONTENT_CREATE,
            Capability.CONTENT_EDIT_TEXT,
            Capability.CONTENT_EDIT_VISUAL,
            Capability.CONTENT_SUBMIT_INTERNAL,
            Capability.CONTENT_REVIEW_INTERNAL,
            Capability.CONTENT_SEND_CLIENT,
            Capability.CONTENT_COMMENT,
            Capability.NOTIFICATION_VIEW_OWN,
            Capability.NOTIFICATION_UPDATE_OWN,
            Capability.PUBLICATION_RECORD,
            Capability.REPORT_VIEW,
            Capability.PROVIDER_CONFIG_VIEW,
            Capability.PROVIDER_CONFIG_MANAGE,
            Capability.AUDIT_VIEW_ORGANIZATION,
        }
    ),
    Role.STRATEGIST: frozenset(
        {
            Capability.ORGANIZATION_VIEW,
            Capability.BUSINESS_VIEW,
            Capability.BUSINESS_MANAGE,
            Capability.BRAND_VIEW,
            Capability.BRAND_MANAGE,
            Capability.SERVICE_MANAGE,
            Capability.AUDIENCE_MANAGE,
            Capability.OBJECTIVE_MANAGE,
            Capability.STRATEGY_VIEW,
            Capability.STRATEGY_MANAGE,
            Capability.STRATEGY_REVIEW_INTERNAL,
            Capability.CALENDAR_VIEW,
            Capability.CALENDAR_MANAGE,
            Capability.PRESET_VIEW,
            Capability.VISUAL_PROMPT_GENERATE,
            Capability.MEDIA_VIEW,
            Capability.CONTENT_VIEW,
            Capability.CONTENT_CREATE,
            Capability.CONTENT_EDIT_TEXT,
            Capability.CONTENT_SUBMIT_INTERNAL,
            Capability.CONTENT_REVIEW_INTERNAL,
            Capability.CONTENT_SEND_CLIENT,
            Capability.CONTENT_COMMENT,
            Capability.NOTIFICATION_VIEW_OWN,
            Capability.NOTIFICATION_UPDATE_OWN,
            Capability.PUBLICATION_RECORD,
            Capability.REPORT_VIEW,
            Capability.PROVIDER_CONFIG_VIEW,
            Capability.AUDIT_VIEW_SCOPED,
        }
    ),
    Role.CONTENT_EDITOR: frozenset(
        {
            Capability.ORGANIZATION_VIEW,
            Capability.BUSINESS_VIEW,
            Capability.BRAND_VIEW,
            Capability.BRAND_MANAGE,
            Capability.SERVICE_MANAGE,
            Capability.AUDIENCE_MANAGE,
            Capability.OBJECTIVE_MANAGE,
            Capability.STRATEGY_VIEW,
            Capability.STRATEGY_MANAGE,
            Capability.CALENDAR_VIEW,
            Capability.CALENDAR_MANAGE,
            Capability.PRESET_VIEW,
            Capability.VISUAL_PROMPT_GENERATE,
            Capability.MEDIA_VIEW,
            Capability.MEDIA_UPLOAD,
            Capability.CONTENT_VIEW,
            Capability.CONTENT_CREATE,
            Capability.CONTENT_EDIT_TEXT,
            Capability.CONTENT_SUBMIT_INTERNAL,
            Capability.CONTENT_COMMENT,
            Capability.NOTIFICATION_VIEW_OWN,
            Capability.NOTIFICATION_UPDATE_OWN,
            Capability.PUBLICATION_RECORD,
            Capability.REPORT_VIEW,
            Capability.AUDIT_VIEW_SCOPED,
        }
    ),
    Role.DESIGNER: frozenset(
        {
            Capability.ORGANIZATION_VIEW,
            Capability.BUSINESS_VIEW,
            Capability.BRAND_VIEW,
            Capability.BRAND_VISUAL_MANAGE,
            Capability.STRATEGY_VIEW,
            Capability.CALENDAR_VIEW,
            Capability.PRESET_VIEW,
            Capability.PRESET_MANAGE,
            Capability.VISUAL_PROMPT_GENERATE,
            Capability.MEDIA_VIEW,
            Capability.MEDIA_UPLOAD,
            Capability.MEDIA_MANAGE,
            Capability.CONTENT_VIEW,
            Capability.CONTENT_EDIT_VISUAL,
            Capability.CONTENT_SUBMIT_INTERNAL,
            Capability.CONTENT_COMMENT,
            Capability.NOTIFICATION_VIEW_OWN,
            Capability.NOTIFICATION_UPDATE_OWN,
            Capability.REPORT_VIEW,
            Capability.AUDIT_VIEW_SCOPED,
        }
    ),
    Role.CLIENT_OWNER: frozenset(
        {
            Capability.ORGANIZATION_VIEW,
            Capability.MEMBERSHIP_VIEW,
            Capability.CLIENT_MEMBERSHIP_MANAGE,
            Capability.CLIENT_INVITATION_MANAGE,
            Capability.BUSINESS_VIEW,
            Capability.BRAND_VIEW,
            Capability.STRATEGY_VIEW,
            Capability.STRATEGY_DECIDE_CLIENT,
            Capability.CALENDAR_VIEW,
            Capability.PRESET_VIEW,
            Capability.MEDIA_VIEW,
            Capability.CONTENT_VIEW,
            Capability.CONTENT_DECIDE_CLIENT,
            Capability.CONTENT_COMMENT,
            Capability.NOTIFICATION_VIEW_OWN,
            Capability.NOTIFICATION_UPDATE_OWN,
            Capability.REPORT_VIEW,
            Capability.AUDIT_VIEW_SCOPED,
        }
    ),
    Role.CLIENT_REVIEWER: frozenset(
        {
            Capability.ORGANIZATION_VIEW,
            Capability.BUSINESS_VIEW,
            Capability.BRAND_VIEW,
            Capability.STRATEGY_VIEW,
            Capability.STRATEGY_DECIDE_CLIENT,
            Capability.CALENDAR_VIEW,
            Capability.PRESET_VIEW,
            Capability.MEDIA_VIEW,
            Capability.CONTENT_VIEW,
            Capability.CONTENT_DECIDE_CLIENT,
            Capability.CONTENT_COMMENT,
            Capability.NOTIFICATION_VIEW_OWN,
            Capability.NOTIFICATION_UPDATE_OWN,
            Capability.REPORT_VIEW,
            Capability.AUDIT_VIEW_SCOPED,
        }
    ),
    Role.VIEWER: frozenset(
        {
            Capability.ORGANIZATION_VIEW,
            Capability.BUSINESS_VIEW,
            Capability.BRAND_VIEW,
            Capability.STRATEGY_VIEW,
            Capability.CALENDAR_VIEW,
            Capability.PRESET_VIEW,
            Capability.MEDIA_VIEW,
            Capability.CONTENT_VIEW,
            Capability.NOTIFICATION_VIEW_OWN,
            Capability.REPORT_VIEW,
        }
    ),
}

ROLE_CAPABILITIES: Final = MappingProxyType(_ROLE_CAPABILITIES)


def capabilities_for(role: Role) -> frozenset[Capability]:
    """Retorna as capacidades imutáveis de um papel oficial."""

    return ROLE_CAPABILITIES.get(role, frozenset())


def has_capability(role: Role, capability: Capability) -> bool:
    """Nega por padrão quando o papel não possui a capacidade."""

    return capability in capabilities_for(role)
