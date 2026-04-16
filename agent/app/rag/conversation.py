from __future__ import annotations

from typing import Protocol

from app.ai.rag.context import build_retrieval_query_from_history


class SupportsRoleContent(Protocol):
    role: str
    content: str


def estimate_tokens_chinese(text: str) -> int:
    return max(1, int(len(text) / 1.5))


def load_history_by_token_budget(
    messages: list[SupportsRoleContent],
    max_tokens: int = 2000,
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    token_budget = 0
    for msg in reversed(messages):
        msg_tokens = estimate_tokens_chinese(msg.content)
        if token_budget + msg_tokens > max_tokens:
            break
        result.append({"role": msg.role, "content": msg.content})
        token_budget += msg_tokens
    return list(reversed(result))


__all__ = [
    "build_retrieval_query_from_history",
    "estimate_tokens_chinese",
    "load_history_by_token_budget",
]
