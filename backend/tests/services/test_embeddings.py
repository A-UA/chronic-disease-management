from unittest.mock import MagicMock

import pytest

from app.services.embeddings import (
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
    get_embedding_provider,
)


def test_mock_embedding_provider_returns_deterministic_vectors():
    provider = MockEmbeddingProvider()

    assert provider.embed_query("abc") == [0.1] * 1536
    assert provider.embed_documents(["x", "y"]) == [[0.1] * 1536, [0.1] * 1536]


def test_get_embedding_provider_returns_mock_provider_by_default():
    provider = get_embedding_provider()

    assert isinstance(provider, MockEmbeddingProvider)


def test_get_embedding_provider_returns_openai_provider_when_configured(monkeypatch):
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr("app.services.embeddings.settings.OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_MODEL", "text-embedding-3-small")
    mock_openai_embeddings = MagicMock()
    monkeypatch.setattr("app.services.embeddings.OpenAIEmbeddings", mock_openai_embeddings)

    provider = get_embedding_provider()

    assert isinstance(provider, OpenAIEmbeddingProvider)
    mock_openai_embeddings.assert_called_once_with(
        model="text-embedding-3-small",
        api_key="test-key",
    )


def test_openai_embedding_provider_delegates_to_client():
    client = MagicMock()
    client.embed_documents.return_value = [[0.2] * 3]
    client.embed_query.return_value = [0.3] * 3
    provider = OpenAIEmbeddingProvider(client)

    assert provider.embed_documents(["hello"]) == [[0.2] * 3]
    assert provider.embed_query("hello") == [0.3] * 3
    client.embed_documents.assert_called_once_with(["hello"])
    client.embed_query.assert_called_once_with("hello")


def test_get_embedding_provider_requires_api_key_for_openai(monkeypatch):
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr("app.services.embeddings.settings.OPENAI_API_KEY", "")

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_embedding_provider()
