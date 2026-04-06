from fastapi import APIRouter
from app.api.endpoints import (
    auth, 
    external_api, 
    documents, 
    knowledge_bases,
    patients,
    family,
    managers,
    chat,
    conversations,
    dashboard,
    audit_logs,
    usage,
    settings,
    rbac,
    organizations,
    users,
    api_keys,
    health_metrics,
    tenants,
    menus,
)

api_router = APIRouter()

# --- Common/Identity ---
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(external_api.router, prefix="/external", tags=["external"])

# --- Unified Resource API (No biz/admin prefix) ---
# Each router implements its own access control via check_permission
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(health_metrics.router, prefix="/health-metrics", tags=["health-metrics"])
api_router.include_router(family.router, prefix="/family", tags=["family"])
api_router.include_router(managers.router, prefix="/managers", tags=["managers"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(knowledge_bases.router, prefix="/kb", tags=["knowledge-bases"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(rbac.router, prefix="/rbac", tags=["rbac"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(menus.router, prefix="/menus", tags=["menus"])

