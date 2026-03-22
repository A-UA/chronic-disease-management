from unittest.mock import MagicMock

import pytest

from app.services.embeddings import (
    OpenAIEmbeddingProvider,
    get_embedding_provider,
)

def test_get_embedding_provider_returns_openai_provider_when_configured(monkeypatch):
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr("app.services.embeddings.settings.OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_BASE_URL", "https://api.xiaomimimo.com/v1")
    mock_client = MagicMock()
    mock_openai_client = MagicMock(return_value=mock_client)
    monkeypatch.setattr("app.services.embeddings.OpenAI", mock_openai_client)

    provider = get_embedding_provider()

    assert isinstance(provider, OpenAIEmbeddingProvider)
    mock_openai_client.assert_called_once_with(
        api_key="test-key",
        base_url="https://api.xiaomimimo.com/v1",
    )


def test_openai_embedding_provider_delegates_to_client():
    client = MagicMock()
    client.embeddings.create.side_effect = [
        MagicMock(data=[MagicMock(embedding=[0.2] * 3)]),
        MagicMock(data=[MagicMock(embedding=[0.3] * 3)]),
    ]
    provider = OpenAIEmbeddingProvider(client, model_name="text-embedding-3-small")

    assert provider.embed_documents(["hello"]) == [[0.2] * 3]
    assert provider.embed_query("hello") == [0.3] * 3
    assert client.embeddings.create.call_count == 2


def test_get_embedding_provider_requires_api_key_for_openai(monkeypatch):
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr("app.services.embeddings.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_API_KEY", "")
    monkeypatch.setattr("app.services.embeddings.settings.LLM_API_KEY", "")

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_embedding_provider()


def test_get_embedding_provider_falls_back_to_llm_key_and_base_url(monkeypatch):
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr("app.services.embeddings.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_API_KEY", "")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_BASE_URL", "")
    monkeypatch.setattr("app.services.embeddings.settings.LLM_API_KEY", "llm-key")
    monkeypatch.setattr("app.services.embeddings.settings.LLM_BASE_URL", "https://api.xiaomimimo.com/v1")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_MODEL", "text-embedding-3-small")
    mock_client = MagicMock()
    mock_openai_client = MagicMock(return_value=mock_client)
    monkeypatch.setattr("app.services.embeddings.OpenAI", mock_openai_client)

    provider = get_embedding_provider()

    assert isinstance(provider, OpenAIEmbeddingProvider)
    mock_openai_client.assert_called_once_with(
        api_key="llm-key",
        base_url="https://api.xiaomimimo.com/v1",
    )
