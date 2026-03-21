from collections.abc import Sequence
from typing import Protocol, TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from app.services.chat import RetrievedChunk


class RerankerProvider(Protocol):
    async def rerank(
        self,
        query: str,
        results: Sequence["RetrievedChunk"],
        limit: int,
    ) -> list["RetrievedChunk"]: ...


class NoopRerankerProvider:
    async def rerank(
        self,
        query: str,
        results: Sequence["RetrievedChunk"],
        limit: int,
    ) -> list["RetrievedChunk"]:
        trimmed = list(results[:limit])
        for result in trimmed:
            result.final_score = result.fused_score
            result.rerank_score = None
        return trimmed


class SimpleRerankerProvider:
    async def rerank(
        self,
        query: str,
        results: Sequence["RetrievedChunk"],
        limit: int,
    ) -> list["RetrievedChunk"]:
        rescored = list(results)
        for result in rescored:
            source_bonus = 0.05 * len(result.sources)
            rerank_score = result.fused_score + source_bonus
            result.rerank_score = rerank_score
            result.final_score = rerank_score

        rescored.sort(key=lambda item: item.final_score, reverse=True)
        return rescored[:limit]


def get_reranker_provider() -> RerankerProvider:
    provider_name = settings.RERANKER_PROVIDER.lower().strip()
    if provider_name in {"", "noop", "none"}:
        return NoopRerankerProvider()
    if provider_name == "simple":
        return SimpleRerankerProvider()
    raise ValueError(f"Unsupported reranker provider: {settings.RERANKER_PROVIDER}")
