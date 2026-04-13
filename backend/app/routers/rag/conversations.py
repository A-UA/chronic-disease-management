"""对话生命周期管理端点 — 纯 HTTP 适配层

对话是用户个人资源，通过 user_id 过滤即可。
tenant_id 通过 RLS 保证隔离。
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.models import User
from app.routers.deps import (
    ConversationServiceDep,
    get_current_user,
    inject_rls_context,
)

router = APIRouter()


# ── Schemas ──


class ConversationRead(BaseModel):
    id: int
    kb_id: int
    title: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageRead(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailRead(BaseModel):
    id: int
    kb_id: int
    title: str | None
    created_at: datetime
    messages: list[MessageRead]

    model_config = ConfigDict(from_attributes=True)


class ConversationUpdate(BaseModel):
    title: str


# ── Endpoints ──


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    service: ConversationServiceDep,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
) -> Any:
    """列出当前用户的对话列表"""
    return await service.list_conversations(current_user.id, tenant_id, skip, limit)


@router.get("/{conversation_id}", response_model=ConversationDetailRead)
async def get_conversation_detail(
    conversation_id: int,
    service: ConversationServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
) -> Any:
    """获取对话详情"""
    return await service.get_conversation_detail(conversation_id, current_user.id, tenant_id)


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def rename_conversation(
    conversation_id: int,
    update_in: ConversationUpdate,
    service: ConversationServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
) -> Any:
    """重命名对话"""
    return await service.rename_conversation(conversation_id, current_user.id, tenant_id, update_in.title)


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    service: ConversationServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
) -> Any:
    """删除对话"""
    await service.delete_conversation(conversation_id, current_user.id, tenant_id)
    return {"status": "ok"}
