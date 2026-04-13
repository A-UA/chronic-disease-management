"""聊天运行时端点 — 纯 HTTP 适配层"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models import User
from app.routers.deps import (
    ChatRuntimeServiceDep,
    ConversationServiceDep,
    get_current_org_id,
    get_current_tenant_id,
    get_current_user,
    get_effective_org_id,
    inject_rls_context,
    verify_quota,
)
from app.schemas.admin import ConversationRead

router = APIRouter()


class ChatRequest(BaseModel):
    kb_id: int
    query: str
    conversation_id: int | None = None
    document_ids: list[int] | None = None
    file_types: list[str] | None = None
    patient_id: int | None = None
    use_agent: bool = False


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    service: ConversationServiceDep,
    skip: int = 0,
    limit: int = 50,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
):
    """[管理员] 获列表"""
    return await service.list_all_conversations(
        tenant_id=tenant_id, effective_org_id=effective_org_id, skip=skip, limit=limit
    )


@router.post("")
async def chat_endpoint(
    request: ChatRequest,
    service: ChatRuntimeServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    _=Depends(verify_quota),
):
    """进行对话"""
    return await service.chat(
        request=request,
        current_user=current_user,
        tenant_id=tenant_id,
        org_id=org_id,
    )
