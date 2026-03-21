from __future__ import annotations

from typing import Any

from app.services.embeddings import EmbeddingProvider


def validate_embedding_provider(provider: EmbeddingProvider, sample_text: str) -> dict[str, Any]:
    try:
        vector = provider.embed_query(sample_text)
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
