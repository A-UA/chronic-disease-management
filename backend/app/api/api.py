from fastapi import APIRouter
from app.api.endpoints import auth, external_api, documents, knowledge_bases
from app.api.endpoints.admin import (
    organizations as admin_orgs,
    dashboard as admin_dashboard,
    users as admin_users,
    patients as admin_patients,
    managers as admin_managers,
    knowledge_bases as admin_kb,
    conversations as admin_convs,
    usage as admin_usage,
    audit_logs as admin_audits,
    settings as admin_settings,
)
from app.api.endpoints.biz import patients, family, managers, chat

api_router = APIRouter()

# --- Public/Common ---
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(external_api.router, prefix="/external", tags=["external"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(
    knowledge_bases.router, prefix="/kb", tags=["knowledge-bases"]
)

# --- Admin (B-side) ---
admin_router = APIRouter()
admin_router.include_router(
    admin_dashboard.router, prefix="/dashboard", tags=["admin-dashboard"]
)
admin_router.include_router(
    admin_orgs.router, prefix="/organizations", tags=["admin-orgs"]
)
admin_router.include_router(admin_users.router, prefix="/users", tags=["admin-users"])
admin_router.include_router(
    admin_patients.router, prefix="/patients", tags=["admin-patients"]
)
admin_router.include_router(
    admin_managers.router, prefix="/managers", tags=["admin-managers"]
)
admin_router.include_router(
    admin_kb.router, prefix="/knowledge-bases", tags=["admin-kb"]
)
admin_router.include_router(
    admin_convs.router, prefix="/conversations", tags=["admin-convs"]
)
admin_router.include_router(admin_usage.router, prefix="/usage", tags=["admin-usage"])
admin_router.include_router(
    admin_audits.router, prefix="/audit-logs", tags=["admin-audits"]
)
admin_router.include_router(
    admin_settings.router, prefix="/settings", tags=["admin-settings"]
)

api_router.include_router(admin_router, prefix="/admin")

# --- Business (C-side/Manager) ---
biz_router = APIRouter()
biz_router.include_router(patients.router, prefix="/patients", tags=["biz-patients"])
biz_router.include_router(family.router, prefix="/family", tags=["biz-family"])
biz_router.include_router(managers.router, prefix="/managers", tags=["biz-managers"])
biz_router.include_router(chat.router, prefix="/chat", tags=["biz-chat"])

api_router.include_router(biz_router, prefix="/biz")
