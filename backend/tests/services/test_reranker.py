from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.chat import RetrievedChunk
from app.services.reranker import NoopRerankerProvider, OpenAICompatibleRerankerProvider, SimpleRerankerProvider, get_reranker_provider


def test_get_reranker_provider_returns_noop_by_default():
    with patch("app.services.reranker.settings.RERANKER_PROVIDER", "noop"):
        provider = get_reranker_provider()

    assert isinstance(provider, NoopRerankerProvider)


def test_get_reranker_provider_returns_simple_provider_when_configured():
    with patch("app.services.reranker.settings.RERANKER_PROVIDER", "simple"):
        provider = get_reranker_provider()

    assert isinstance(provider, SimpleRerankerProvider)


def test_get_reranker_provider_returns_openai_compatible_provider_when_configured():
    with patch("app.services.reranker.settings.RERANKER_PROVIDER", "openai_compatible"), patch(
        "app.services.reranker.settings.RERANKER_API_KEY",
        "secret",
    ), patch(
        "app.services.reranker.settings.RERANKER_BASE_URL",
        "https://api.xiaomimimo.com/v1",
    ), patch(
        "app.services.reranker.settings.RERANKER_MODEL",
        "mimo-v2-flash",
    ):
        mock_client = MagicMock()
        mock_async_openai = MagicMock(return_value=mock_client)
        with patch("app.services.reranker.AsyncOpenAI", mock_async_openai):
            provider = get_reranker_provider()

    assert isinstance(provider, OpenAICompatibleRerankerProvider)
    mock_async_openai.assert_called_once_with(
        api_key="secret",
        base_url="https://api.xiaomimimo.com/v1",
    )


@pytest.mark.asyncio
async def test_openai_compatible_reranker_provider_maps_ranked_results():
    chunk_a = SimpleNamespace(id=uuid4(), content="A")
    chunk_b = SimpleNamespace(id=uuid4(), content="B")
    result_a = RetrievedChunk(chunk=chunk_a, fused_score=0.2, final_score=0.2, sources=("vector",))
    result_b = RetrievedChunk(chunk=chunk_b, fused_score=0.3, final_score=0.3, sources=("vector", "keyword"))

    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"ranked_results":[{"chunk_id":"' + str(chunk_a.id) + '","score":0.91},{"chunk_id":"' + str(chunk_b.id) + '","score":0.52}]}'
                )
            )
        ]
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=response)
    provider = OpenAICompatibleRerankerProvider(mock_client, model_name="mimo-v2-flash")

    ranked = await provider.rerank("血糖高怎么办?", [result_b, result_a], limit=2)

    assert [item.chunk.id for item in ranked] == [chunk_a.id, chunk_b.id]
    assert ranked[0].rerank_score == 0.91
    assert ranked[0].final_score == 0.91
    mock_client.chat.completions.create.assert_awaited_once()
