from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List

from app.api.deps import get_db, get_current_org, check_permission
from app.db.models import Conversation, Message
from app.schemas.admin import ConversationRead, MessageRead

router = APIRouter()


@router.get("/", response_model=List[ConversationRead])
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    org_id: UUID = Depends(get_current_org),
    _org_user=Depends(check_permission("org:view_usage")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Conversation)
        .where(Conversation.org_id == org_id)
        .offset(skip)
        .limit(limit)
        .order_by(Conversation.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{conversation_id}/messages", response_model=List[MessageRead])
async def get_messages(
    conversation_id: UUID,
    org_id: UUID = Depends(get_current_org),
    _org_user=Depends(check_permission("org:view_usage")),
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conversation_id)
    if not conv or conv.org_id != org_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()
