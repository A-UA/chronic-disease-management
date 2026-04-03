"""对话生命周期管理端点"""
from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_org, get_db
from app.db.models import User, Conversation, Message

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
    messages: List[MessageRead]

    model_config = ConfigDict(from_attributes=True)


class ConversationUpdate(BaseModel):
    title: str


# ── Endpoints ──

@router.get("", response_model=List[ConversationRead])
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """列出当前用户的对话列表"""
    stmt = (
        select(Conversation)
        .where(
            Conversation.user_id == current_user.id,
            Conversation.org_id == org_id,
        )
        .order_by(Conversation.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{conversation_id}", response_model=ConversationDetailRead)
async def get_conversation_detail(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取对话详情，包含消息历史"""
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if conv.org_id != org_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return {
        "id": conv.id,
        "kb_id": conv.kb_id,
        "title": conv.title,
        "created_at": conv.created_at,
        "messages": messages,
    }


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def rename_conversation(
    conversation_id: int,
    update_in: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """重命名对话"""
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != current_user.id or conv.org_id != org_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    conv.title = update_in.title
    await db.commit()
    await db.refresh(conv)
    return conv


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """删除对话及其所有消息"""
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != current_user.id or conv.org_id != org_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.delete(conv)
    await db.commit()
    return {"status": "ok"}
