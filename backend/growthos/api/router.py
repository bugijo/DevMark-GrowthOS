from fastapi import APIRouter

from growthos.api.routes import (
    ai,
    audit_logs,
    auth,
    businesses,
    catalogs,
    comparisons,
    contents,
    health,
    invitations,
    landing,
    media,
    members,
    notifications,
    onboarding,
    organizations,
    planning,
    privacy,
    providers,
    reports,
    sales,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(ai.router, tags=["ai"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(invitations.router, prefix="/auth", tags=["auth"])
api_router.include_router(members.router, prefix="/members", tags=["members"])
api_router.include_router(media.router, tags=["media"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(businesses.router, prefix="/businesses", tags=["businesses"])
api_router.include_router(catalogs.router, tags=["brand"])
api_router.include_router(comparisons.router, tags=["comparisons"])
api_router.include_router(planning.router, tags=["planning"])
api_router.include_router(reports.router, tags=["reports"])
api_router.include_router(sales.router, tags=["sales"])
api_router.include_router(landing.router, tags=["landing"])
api_router.include_router(providers.router, tags=["providers"])
api_router.include_router(privacy.router, tags=["privacy"])
api_router.include_router(contents.router, prefix="/contents", tags=["contents"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(onboarding.router, tags=["onboarding"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit"])
