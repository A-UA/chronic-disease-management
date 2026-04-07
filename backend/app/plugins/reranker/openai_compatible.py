"""OpenAI Compatible Reranker — 基于 LLM 的重排序"""
import json
import logging
from collections.abc import Sequence
from typing import Any

from openai import AsyncOpenAI

from app.base.config import settings
from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


class OpenAICompatibleRerankerPlugin:
    def __init__(self, client: AsyncOpenAI, model_name: str):
        self.client = client
        self.model_name = model_name

    async def rerank(
        self,
        query: str,
        results: Sequence[Any],
        limit: int,
    ) -> list[Any]:
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
        ranked_results: list[Any] = []
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

        # 回退到 noop
        fallback = list(results[:limit])
        for result in fallback:
            result.final_score = result.fused_score
            result.rerank_score = None
        return fallback


def _create_openai_reranker() -> OpenAICompatibleRerankerPlugin:
    api_key = settings.RERANKER_API_KEY or settings.LLM_API_KEY
    base_url = settings.RERANKER_BASE_URL or settings.LLM_BASE_URL
    model_name = settings.RERANKER_MODEL or settings.CHAT_MODEL
    if not api_key:
        raise ValueError("请设置 RERANKER_API_KEY")
    if not base_url:
        raise ValueError("请设置 RERANKER_BASE_URL")
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return OpenAICompatibleRerankerPlugin(client, model_name=model_name)


PluginRegistry.register("reranker", "openai_compatible", _create_openai_reranker)
