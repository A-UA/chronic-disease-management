from fastapi import APIRouter
from app.api.endpoints import chat, documents, external_api, auth, organizations, knowledge_bases, patients, family

api_router = APIRouter()

# 认证模块
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# 组织管理
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])

# 医疗画像
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(family.router, prefix="/family", tags=["family"])

# 知识库管理
api_router.include_router(knowledge_bases.router, prefix="/kb", tags=["knowledge_bases"])

# 挂载内部聊天 API
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

# 挂载文档管理 API
api_router.include_router(documents.router, tags=["documents"])

# 挂载外部开发者 API (兼容 OpenAI 风格等)
api_router.include_router(external_api.router, prefix="/external", tags=["external"])
