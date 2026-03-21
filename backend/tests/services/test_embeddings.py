from app.services.embeddings import MockEmbeddingProvider, get_embedding_provider


def test_mock_embedding_provider_returns_deterministic_vectors():
    provider = MockEmbeddingProvider()

    assert provider.embed_query("abc") == [0.1] * 1536
    assert provider.embed_documents(["x", "y"]) == [[0.1] * 1536, [0.1] * 1536]


def test_get_embedding_provider_returns_mock_provider_by_default():
    provider = get_embedding_provider()

    assert isinstance(provider, MockEmbeddingProvider)
