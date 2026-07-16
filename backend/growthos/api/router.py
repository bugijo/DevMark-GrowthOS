from fastapi import APIRouter

from growthos.api.routes import (
    audit_logs,
    auth,
    businesses,
    catalogs,
    contents,
    health,
    invitations,
    media,
    members,
    notifications,
    organizations,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(invitations.router, prefix="/auth", tags=["auth"])
api_router.include_router(members.router, prefix="/members", tags=["members"])
api_router.include_router(media.router, tags=["media"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(businesses.router, prefix="/businesses", tags=["businesses"])
api_router.include_router(catalogs.router, tags=["brand"])
api_router.include_router(contents.router, prefix="/contents", tags=["contents"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit"])
