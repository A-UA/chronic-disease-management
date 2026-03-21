from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message
from app.services.query_rewrite import normalize_query

_FOLLOW_UP_MARKERS = (
    "\u8fd9\u4e2a",
    "\u8fd9\u4e2a\u836f",
    "\u8fd9\u4e2a\u7ed3\u679c",
    "\u8fd9\u4e2a\u60c5\u51b5",
    "\u7ee7\u7eed",
    "\u8fd8\u8981",
    "\u90a3",
    "\u662f\u5426",
)


def build_retrieval_query_from_history(current_query: str, history_messages: list[dict[str, str]]) -> str:
    normalized_current = normalize_query(current_query)
    if not normalized_current:
        return ""

    is_follow_up = any(marker in normalized_current for marker in _FOLLOW_UP_MARKERS) or len(normalized_current) <= 12
    if not is_follow_up:
        return normalized_current

    recent_user_context = ""
    for item in reversed(history_messages):
        if item.get("role") == "user":
            recent_user_context = normalize_query(item.get("content", ""))
            if recent_user_context:
                break

    if not recent_user_context or recent_user_context == normalized_current:
        return normalized_current

    return f"{recent_user_context} {normalized_current}".strip()


async def load_recent_conversation_messages(
    db: AsyncSession,
    conversation_id: UUID,
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
    conversation_id: UUID,
    current_query: str,
) -> str:
    history = await load_recent_conversation_messages(db, conversation_id)
    return build_retrieval_query_from_history(current_query=current_query, history_messages=history)
