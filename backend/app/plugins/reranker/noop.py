"""Noop Reranker — 不重排序，直接截断"""
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from app.plugins.registry import PluginRegistry

if TYPE_CHECKING:
    from app.services.chat import RetrievedChunk


class NoopRerankerPlugin:
    async def rerank(
        self,
        query: str,
        results: Sequence[Any],
        limit: int,
    ) -> list[Any]:
        trimmed = list(results[:limit])
        for result in trimmed:
            result.final_score = result.fused_score
            result.rerank_score = None
        return trimmed


PluginRegistry.register("reranker", "noop", lambda: NoopRerankerPlugin())
