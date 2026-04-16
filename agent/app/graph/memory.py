"""Agent 对话记忆 — 桥接现有 conversation_context.py + conversation_compress.py

不重写记忆逻辑，复用已有的：
- conversation_context.is_likely_follow_up + build_retrieval_query_from_history
- conversation_compress.maybe_compress_history
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from app.ai.agent.security import SecurityContext
from app.ai.rag.context import (
    build_retrieval_query_from_history,
    is_likely_follow_up,
)
from app.models import Message

logger = logging.getLogger(__name__)


async def load_conversation_history(
    ctx: SecurityContext,
    conversation_id: int,
    max_messages: int = 20,
) -> list[dict[str, str]]:
    """加载对话历史（走 RLS）"""
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(max_messages)
    )
    result = await ctx.db.execute(stmt)
    messages = list(reversed(result.scalars().all()))
    return [{"role": m.role, "content": m.content} for m in messages]


async def prepare_query_with_memory(
    ctx: SecurityContext,
    query: str,
    conversation_id: int | None,
) -> tuple[str, list[dict[str, str]]]:
    """用对话记忆增强查询

    Returns:
        (enhanced_query, history_messages)
    """
    if not conversation_id:
        return query, []

    history = await load_conversation_history(ctx, conversation_id)
    if not history:
        return query, []

    # 追问检测 + 上下文增强（复用现有逻辑）
    if is_likely_follow_up(query):
        enhanced = build_retrieval_query_from_history(query, history)
        return enhanced, history

    return query, history


async def save_message(
    ctx: SecurityContext,
    conversation_id: int,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> Message:
    """保存消息到对话（走 RLS）"""
    from app.base.snowflake import generate_id

    msg = Message(
        id=generate_id(),
        conversation_id=conversation_id,
        tenant_id=ctx.tenant_id,
        org_id=ctx.org_id,
        role=role,
        content=content,
        metadata_=metadata or {},
    )
    ctx.db.add(msg)
    await ctx.db.flush()
    return msg


async def maybe_compress(
    ctx: SecurityContext,
    conversation_id: int,
) -> None:
    """检查是否需要压缩对话历史（复用现有逻辑）"""
    from app.ai.rag.compress import maybe_compress_history
    from app.plugins.registry import PluginRegistry

    llm = PluginRegistry.get("llm")
    await maybe_compress_history(ctx.db, conversation_id, llm)
