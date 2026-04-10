from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import SecurityContext, run_agent
from app.base.database import AsyncSessionLocal
from app.models import (
    Conversation,
    Message,
    OrganizationUser,
    OrganizationUserRole,
    User,
)
from app.services.system.rbac import RBACService


def _generate_title(query: str, max_len: int = 50) -> str:
    match = re.search(r"[。？！?!]", query)
    if match and match.end() <= max_len:
        return query[: match.end()]
    if len(query) <= max_len:
        return query
    truncated = query[:max_len]
    last_break = max(truncated.rfind(" "), truncated.rfind("。"), truncated.rfind("，"))
    if last_break > max_len // 2:
        return truncated[:last_break] + "..."
    return truncated + "..."


async def build_agent_permissions(db: AsyncSession, role_ids: list[int]) -> set[str]:
    if not role_ids:
        return set()
    return await RBACService.get_effective_permissions(db, role_ids)


async def handle_agent_chat(
    *,
    request,
    db: AsyncSession,
    tenant_id: int,
    org_id: int,
    current_user: User,
) -> StreamingResponse:
    ou_stmt = select(OrganizationUser).where(
        OrganizationUser.user_id == current_user.id,
        OrganizationUser.org_id == org_id,
    )
    ou_result = await db.execute(ou_stmt)
    org_user = ou_result.scalar_one_or_none()

    role_ids: list[int] = []
    if org_user is not None:
        role_stmt = select(OrganizationUserRole).where(
            OrganizationUserRole.org_id == org_id,
            OrganizationUserRole.user_id == current_user.id,
        )
        role_result = await db.execute(role_stmt)
        role_ids = [role.role_id for role in role_result.scalars().all()]

    effective_perms = await build_agent_permissions(db, role_ids)
    ctx = SecurityContext(
        tenant_id=tenant_id,
        org_id=org_id,
        user_id=current_user.id,
        roles=(),
        permissions=frozenset(effective_perms),
        db=db,
    )

    conversation: Conversation | None = None
    if request.conversation_id is not None:
        conversation = await db.get(Conversation, request.conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if (
            conversation.tenant_id != tenant_id
            or conversation.user_id != current_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="Conversation does not belong to current user",
            )
        if conversation.kb_id != request.kb_id:
            raise HTTPException(
                status_code=400,
                detail="Conversation knowledge base mismatch",
            )

    if conversation is None:
        from app.base.snowflake import get_next_id

        conversation = Conversation(
            id=get_next_id(),
            kb_id=request.kb_id,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=current_user.id,
            title=_generate_title(request.query),
        )
        db.add(conversation)

    user_msg = Message(
        conversation_id=conversation.id,
        tenant_id=tenant_id,
        org_id=org_id,
        role="user",
        content=request.query,
        metadata_={"agent_mode": True},
    )
    db.add(user_msg)
    await db.commit()

    agent_result = await run_agent(
        ctx=ctx,
        query=request.query,
        kb_id=request.kb_id,
        conversation_id=conversation.id,
    )
    answer = agent_result.get("answer", "")
    citations = agent_result.get("citations", [])
    skill_results = agent_result.get("skill_results", [])

    async with AsyncSessionLocal() as db_save:
        await db_save.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )
        await db_save.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(current_user.id)},
        )
        assistant_msg = Message(
            conversation_id=conversation.id,
            tenant_id=tenant_id,
            org_id=org_id,
            role="assistant",
            content=answer or "[Agent response interrupted]",
            metadata_={
                "citations": citations,
                "skill_results": skill_results,
                "agent_mode": True,
            },
        )
        db_save.add(assistant_msg)
        await db_save.commit()

    async def generate_agent() -> AsyncGenerator[str, None]:
        yield (
            "event: meta\ndata: "
            f"{json.dumps({'conversation_id': str(conversation.id), 'citations': citations})}\n\n"
        )
        if answer:
            yield f"event: chunk\ndata: {json.dumps({'text': answer})}\n\n"
        done_data = {
            "tokens": 0,
            "statement_citations": [],
            "skill_results": skill_results,
        }
        yield f"event: done\ndata: {json.dumps(done_data)}\n\n"

    return StreamingResponse(generate_agent(), media_type="text/event-stream")
