"""Simple Reranker — 基于来源数量的简单加分重排序"""
from collections.abc import Sequence
from typing import Any

from app.plugins.registry import PluginRegistry


class SimpleRerankerPlugin:
    async def rerank(
        self,
        query: str,
        results: Sequence[Any],
        limit: int,
    ) -> list[Any]:
        rescored = list(results)
        for result in rescored:
            source_bonus = 0.05 * len(result.sources)
            rerank_score = result.fused_score + source_bonus
            result.rerank_score = rerank_score
            result.final_score = rerank_score
        rescored.sort(key=lambda item: item.final_score, reverse=True)
        return rescored[:limit]


PluginRegistry.register("reranker", "simple", lambda: SimpleRerankerPlugin())
