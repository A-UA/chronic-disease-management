from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, User
from app.routers.deps import (
    get_current_org_id,
    get_current_tenant_id,
    get_current_user,
    get_db,
    get_effective_org_id,
    inject_rls_context,
    verify_quota,
)
from app.schemas.admin import ConversationRead
from app.services.agent.service import handle_agent_chat
from app.services.rag.chat_service import handle_standard_chat

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
    skip: int = 0,
    limit: int = 50,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Conversation).where(Conversation.tenant_id == tenant_id)
    if effective_org_id is not None:
        stmt = stmt.where(Conversation.org_id == effective_org_id)
    stmt = stmt.offset(skip).limit(limit).order_by(Conversation.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("")
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    _=Depends(verify_quota),
    db: AsyncSession = Depends(get_db),
):
    if request.use_agent:
        return await handle_agent_chat(
            request=request,
            db=db,
            tenant_id=tenant_id,
            org_id=org_id,
            current_user=current_user,
        )

    return await handle_standard_chat(
        request=request,
        current_user=current_user,
        tenant_id=tenant_id,
        org_id=org_id,
        db=db,
    )
