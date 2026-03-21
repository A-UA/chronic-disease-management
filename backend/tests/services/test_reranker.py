from unittest.mock import patch

from app.services.reranker import NoopRerankerProvider, SimpleRerankerProvider, get_reranker_provider


def test_get_reranker_provider_returns_noop_by_default():
    with patch("app.services.reranker.settings.RERANKER_PROVIDER", "noop"):
        provider = get_reranker_provider()

    assert isinstance(provider, NoopRerankerProvider)


def test_get_reranker_provider_returns_simple_provider_when_configured():
    with patch("app.services.reranker.settings.RERANKER_PROVIDER", "simple"):
        provider = get_reranker_provider()

    assert isinstance(provider, SimpleRerankerProvider)
