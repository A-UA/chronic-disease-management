from __future__ import annotations

from typing import Any

from app.ai.rag.embeddings import EmbeddingProvider


async def validate_embedding_provider(
    provider: EmbeddingProvider, sample_text: str
) -> dict[str, Any]:
    """验证 Embedding Provider 是否可用，已改为异步"""
    try:
        vector = await provider.embed_query(sample_text)
        return {
            "ok": True,
            "vector_length": len(vector),
            "preview": vector[:5],
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "vector_length": 0,
            "preview": [],
            "error": str(exc),
        }
