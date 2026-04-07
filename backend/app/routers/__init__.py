"""API Router - all routes from modules"""
from fastapi import APIRouter

# Audit module
from app.routers.audit.router import router as audit_logs_router

# Auth module
from app.routers.auth.router import router as auth_router
from app.routers.patient.family import router as family_router
from app.routers.patient.health_metrics import router as health_metrics_router
from app.routers.patient.managers import router as managers_router

# Patient module
from app.routers.patient.patients import router as patients_router

# RAG module
from app.routers.rag.chat import router as chat_router
from app.routers.rag.conversations import router as conversations_router
from app.routers.rag.documents import router as documents_router
from app.routers.rag.knowledge_bases import router as kb_router
from app.routers.system.api_keys import router as api_keys_router
from app.routers.system.dashboard import router as dashboard_router
from app.routers.system.external_api import router as external_api_router
from app.routers.system.menus import router as menus_router

# System module
from app.routers.system.organizations import router as organizations_router
from app.routers.system.rbac import router as rbac_router
from app.routers.system.settings import router as settings_router
from app.routers.system.tenants import router as tenants_router
from app.routers.system.usage import router as usage_router
from app.routers.system.users import router as users_router

api_router = APIRouter()

# --- Auth ---
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(external_api_router, prefix="/external", tags=["external"])

# --- System ---
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(organizations_router, prefix="/organizations", tags=["organizations"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(rbac_router, prefix="/rbac", tags=["rbac"])
api_router.include_router(menus_router, prefix="/menus", tags=["menus"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(api_keys_router, prefix="/api-keys", tags=["api-keys"])
api_router.include_router(usage_router, prefix="/usage", tags=["usage"])
api_router.include_router(tenants_router, prefix="/tenants", tags=["tenants"])

# --- Patient ---
api_router.include_router(patients_router, prefix="/patients", tags=["patients"])
api_router.include_router(health_metrics_router, prefix="/health-metrics", tags=["health-metrics"])
api_router.include_router(family_router, prefix="/family", tags=["family"])
api_router.include_router(managers_router, prefix="/managers", tags=["managers"])

# --- RAG ---
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(conversations_router, prefix="/conversations", tags=["conversations"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(kb_router, prefix="/kb", tags=["knowledge-bases"])

# --- Audit ---
api_router.include_router(audit_logs_router, prefix="/audit-logs", tags=["audit-logs"])
