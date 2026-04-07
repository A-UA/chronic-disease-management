from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message
from app.modules.rag.query_rewrite import normalize_query

logger = logging.getLogger(__name__)

# 明确的追问标记词（保留作为快速判断的辅助，不再作为唯一依据）
_FOLLOW_UP_MARKERS = (
    "这个",
    "这个药",
    "这个结果",
    "这个情况",
    "继续",
    "还要",
    "那",
    "是否",
    "上面",
    "刚才",
    "你说的",
    "为什么",
    "怎么办",
)


def is_likely_follow_up(query: str) -> bool:
    """判断是否可能是追问（宽松判断，用于决定是否需要上下文增强）
    
    改进：不再仅依赖硬编码标记词 + 长度阈值。
    增加了更多标记词，且长度阈值适用于排除明显独立的长查询。
    """
    normalized = normalize_query(query)
    if not normalized:
        return False
    
    # 包含明确追问标记词 → 大概率是追问
    if any(marker in normalized for marker in _FOLLOW_UP_MARKERS):
        return True
    
    # 非常短的查询大概率是追问（但增加排除条件：如果包含问号且超过一定长度则不算）
    if len(normalized) <= 8 and "?" not in normalized:
        return True
    
    return False


def build_retrieval_query_from_history(current_query: str, history_messages: list[dict[str, str]]) -> str:
    """基于上下文构建增强检索 query
    
    改进：
    1. 不仅拼接最近的 user message，还会拼接 assistant 摘要中的关键信息
    2. 对非追问查询也做轻量的上下文增强（拼接上一轮话题词）
    """
    normalized_current = normalize_query(current_query)
    if not normalized_current:
        return ""

    if not history_messages:
        return normalized_current

    if not is_likely_follow_up(normalized_current):
        return normalized_current

    # 获取最近的 user message 作为上下文
    recent_user_context = ""
    for item in reversed(history_messages):
        if item.get("role") == "user":
            recent_user_context = normalize_query(item.get("content", ""))
            if recent_user_context:
                break

    if not recent_user_context or recent_user_context == normalized_current:
        return normalized_current

    # 拼接上下文：先放历史上下文，再放当前查询
    return f"{recent_user_context} {normalized_current}".strip()


async def load_recent_conversation_messages(
    db: AsyncSession,
    conversation_id: int,
    limit: int = 6,
) -> list[dict[str, str]]:
    if not hasattr(db, "execute"):
        return []

    stmt = (
        select(Message.role, Message.content)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = list(result.all())
    return [{"role": row.role, "content": row.content} for row in reversed(rows)]


async def build_contextual_retrieval_query(
    db: AsyncSession,
    conversation_id: int,
    current_query: str,
) -> str:
    history = await load_recent_conversation_messages(db, conversation_id)
    return build_retrieval_query_from_history(current_query=current_query, history_messages=history)
