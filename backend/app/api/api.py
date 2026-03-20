from fastapi import APIRouter
from app.api.endpoints import auth, external_api, documents
from app.api.endpoints.admin import organizations as admin_orgs
from app.api.endpoints.biz import patients, family, managers, chat

api_router = APIRouter()

# --- Public/Common ---
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(external_api.router, prefix="/external", tags=["external"])

# --- Admin (B-side) ---
admin_router = APIRouter()
admin_router.include_router(admin_orgs.router, prefix="/organizations", tags=["admin-orgs"])
# admin_router.include_router(knowledge_bases.router, prefix="/kb", tags=["admin-kb"])
# admin_router.include_router(documents.router, prefix="/documents", tags=["admin-docs"])

api_router.include_router(admin_router, prefix="/admin")

# --- Business (C-side/Manager) ---
biz_router = APIRouter()
biz_router.include_router(patients.router, prefix="/patients", tags=["biz-patients"])
biz_router.include_router(family.router, prefix="/family", tags=["biz-family"])
biz_router.include_router(managers.router, prefix="/managers", tags=["biz-managers"])
biz_router.include_router(chat.router, prefix="/chat", tags=["biz-chat"])

api_router.include_router(biz_router, prefix="/biz")

# --- Compatibility Layer (Optional: for existing tests or old clients) ---
# To keep existing tests passing, we can still mount them at root as well
api_router.include_router(admin_orgs.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(family.router, prefix="/family", tags=["family"])
api_router.include_router(managers.router, prefix="/managers", tags=["managers"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(documents.router, tags=["documents"])
