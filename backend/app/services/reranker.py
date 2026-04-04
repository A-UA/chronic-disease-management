import json
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from openai import AsyncOpenAI

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


class OpenAICompatibleRerankerProvider:
    def __init__(self, client: AsyncOpenAI, model_name: str):
        self.client = client
        self.model_name = model_name

    async def rerank(
        self,
        query: str,
        results: Sequence["RetrievedChunk"],
        limit: int,
    ) -> list["RetrievedChunk"]:
        if not results:
            return []

        payload = [
            {"chunk_id": str(result.chunk.id), "content": result.chunk.content}
            for result in results
        ]
        prompt = (
            "You are a retrieval reranker. Rank the most relevant chunks for the user query. "
            "Return strict JSON with the shape {\"ranked_results\":[{\"chunk_id\":\"...\",\"score\":0.0}]}. "
            "Use higher score for more relevant chunks and include at most the requested limit.\n\n"
            f"Query: {query}\n"
            f"Limit: {limit}\n"
            f"Candidates: {json.dumps(payload, ensure_ascii=False)}"
        )
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        content = response.choices[0].message.content if response.choices else ""
        parsed = json.loads(content or "{}")
        ranked_payload = parsed.get("ranked_results", [])

        result_by_id = {str(result.chunk.id): result for result in results}
        ranked_results: list["RetrievedChunk"] = []
        for item in ranked_payload:
            chunk_id = item.get("chunk_id")
            score = item.get("score")
            result = result_by_id.get(chunk_id)
            if result is None or score is None:
                continue
            result.rerank_score = float(score)
            result.final_score = float(score)
            ranked_results.append(result)
            if len(ranked_results) >= limit:
                break

        if ranked_results:
            return ranked_results

        fallback = list(results[:limit])
        for result in fallback:
            result.final_score = result.fused_score
            result.rerank_score = None
        return fallback


def get_reranker_provider() -> RerankerProvider:
    provider_name = settings.RERANKER_PROVIDER.lower().strip()
    if provider_name in {"", "noop", "none"}:
        return NoopRerankerProvider()
    if provider_name == "simple":
        return SimpleRerankerProvider()
    if provider_name == "zhipu":
        api_key = settings.RERANKER_API_KEY or settings.LLM_API_KEY
        if not api_key:
            raise ValueError("RERANKER_API_KEY is required when RERANKER_PROVIDER=zhipu")
        base_url = settings.RERANKER_BASE_URL or "https://open.bigmodel.cn/api/paas/v4/"
        model_name = settings.RERANKER_MODEL or "reranker"
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        return OpenAICompatibleRerankerProvider(client, model_name=model_name)
    if provider_name in {"openai_compatible", "xiaomi_mimo"}:
        api_key = settings.RERANKER_API_KEY or settings.LLM_API_KEY
        base_url = settings.RERANKER_BASE_URL or settings.LLM_BASE_URL
        model_name = settings.RERANKER_MODEL or settings.CHAT_MODEL
        if not api_key:
            raise ValueError("RERANKER_API_KEY is required when RERANKER_PROVIDER=openai_compatible")
        if not base_url:
            raise ValueError("RERANKER_BASE_URL is required when RERANKER_PROVIDER=openai_compatible")
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        return OpenAICompatibleRerankerProvider(client, model_name=model_name)
    raise ValueError(f"Unsupported reranker provider: {settings.RERANKER_PROVIDER}")
