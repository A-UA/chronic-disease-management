from collections.abc import Sequence
from typing import Protocol, TYPE_CHECKING

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
        return list(results[:limit])


def get_reranker_provider() -> RerankerProvider:
    return NoopRerankerProvider()
