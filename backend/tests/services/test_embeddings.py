"""Embedding Provider 测试：验证 AsyncOpenAI 异步接口、Provider 选择、API Key fallback"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.embeddings import OpenAIEmbeddingProvider, get_embedding_provider


def test_get_embedding_provider_openai(monkeypatch):
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr("app.services.embeddings.settings.OPENAI_API_KEY", "k")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_MODEL", "m")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_BASE_URL", "http://x")
    mock_cls = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("app.services.embeddings.AsyncOpenAI", mock_cls)
    p = get_embedding_provider()
    assert isinstance(p, OpenAIEmbeddingProvider)
    mock_cls.assert_called_once_with(api_key="k", base_url="http://x")


def test_get_embedding_provider_requires_key(monkeypatch):
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr("app.services.embeddings.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_API_KEY", "")
    monkeypatch.setattr("app.services.embeddings.settings.LLM_API_KEY", "")
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_embedding_provider()


def test_get_embedding_provider_llm_key_fallback(monkeypatch):
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr("app.services.embeddings.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_API_KEY", "")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_BASE_URL", "")
    monkeypatch.setattr("app.services.embeddings.settings.LLM_API_KEY", "llm-k")
    monkeypatch.setattr("app.services.embeddings.settings.LLM_BASE_URL", "http://llm")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_MODEL", "m")
    mock_cls = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("app.services.embeddings.AsyncOpenAI", mock_cls)
    get_embedding_provider()
    mock_cls.assert_called_once_with(api_key="llm-k", base_url="http://llm")


@pytest.mark.asyncio
async def test_embed_documents_async():
    client = MagicMock()
    client.embeddings.create = AsyncMock(
        return_value=MagicMock(data=[MagicMock(embedding=[0.1, 0.2])])
    )
    p = OpenAIEmbeddingProvider(client, "m")
    result = await p.embed_documents(["hi"])
    assert result == [[0.1, 0.2]]
    assert p.get_dimension() == 2


@pytest.mark.asyncio
async def test_embed_query_async():
    client = MagicMock()
    client.embeddings.create = AsyncMock(
        return_value=MagicMock(data=[MagicMock(embedding=[0.3])])
    )
    p = OpenAIEmbeddingProvider(client, "m")
    result = await p.embed_query("q")
    assert result == [0.3]


@pytest.mark.asyncio
async def test_embed_documents_empty():
    p = OpenAIEmbeddingProvider(MagicMock(), "m")
    assert await p.embed_documents([]) == []


@pytest.mark.asyncio
async def test_embed_query_empty():
    p = OpenAIEmbeddingProvider(MagicMock(), "m")
    assert await p.embed_query("") == []
