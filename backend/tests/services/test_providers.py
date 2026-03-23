"""LLM / Reranker / Storage / Quota provider 测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.llm import get_llm_provider
from app.services.reranker import (
    NoopRerankerProvider,
    SimpleRerankerProvider,
    get_reranker_provider,
)
from app.services.quota import check_quota_during_stream


# ── LLM Provider ──

def test_get_llm_requires_key(monkeypatch):
    monkeypatch.setattr("app.services.llm.settings.LLM_PROVIDER", "openai_compatible")
    monkeypatch.setattr("app.services.llm.settings.LLM_API_KEY", "")
    monkeypatch.setattr("app.services.llm.settings.LLM_BASE_URL", "http://x")
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        get_llm_provider()


def test_get_llm_requires_url(monkeypatch):
    monkeypatch.setattr("app.services.llm.settings.LLM_PROVIDER", "openai_compatible")
    monkeypatch.setattr("app.services.llm.settings.LLM_API_KEY", "k")
    monkeypatch.setattr("app.services.llm.settings.LLM_BASE_URL", "")
    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        get_llm_provider()


def test_get_llm_unsupported(monkeypatch):
    monkeypatch.setattr("app.services.llm.settings.LLM_PROVIDER", "banana")
    with pytest.raises(ValueError, match="Unsupported"):
        get_llm_provider()


# ── Reranker ──

def test_noop_reranker(monkeypatch):
    monkeypatch.setattr("app.services.reranker.settings.RERANKER_PROVIDER", "noop")
    p = get_reranker_provider()
    assert isinstance(p, NoopRerankerProvider)


def test_simple_reranker(monkeypatch):
    monkeypatch.setattr("app.services.reranker.settings.RERANKER_PROVIDER", "simple")
    p = get_reranker_provider()
    assert isinstance(p, SimpleRerankerProvider)


@pytest.mark.asyncio
async def test_noop_reranker_passthrough():
    r = NoopRerankerProvider()
    a = MagicMock(fused_score=0.5, final_score=0.0, rerank_score=None)
    b = MagicMock(fused_score=0.8, final_score=0.0, rerank_score=None)
    results = await r.rerank("q", [a, b], 2)
    assert len(results) == 2
    assert a.final_score == 0.5


@pytest.mark.asyncio
async def test_simple_reranker_sorts():
    r = SimpleRerankerProvider()
    a = MagicMock(fused_score=0.3, sources=("vector",), final_score=0.0, rerank_score=None)
    b = MagicMock(fused_score=0.7, sources=("vector", "keyword"), final_score=0.0, rerank_score=None)
    results = await r.rerank("q", [a, b], 2)
    assert results[0] is b  # b 有更高分


# ── Quota ──

@pytest.mark.asyncio
async def test_check_quota_redis_ok():
    with patch("app.services.quota.get_redis_client") as mock_redis:
        mock_redis.return_value.get = AsyncMock(return_value="100")
        ok = await check_quota_during_stream(uuid4(), 50)
        assert ok is True


@pytest.mark.asyncio
async def test_check_quota_redis_exceeded():
    with patch("app.services.quota.get_redis_client") as mock_redis:
        mock_redis.return_value.get = AsyncMock(return_value="10")
        ok = await check_quota_during_stream(uuid4(), 50)
        assert ok is False


@pytest.mark.asyncio
async def test_check_quota_redis_miss_no_db():
    with patch("app.services.quota.get_redis_client") as mock_redis:
        mock_redis.return_value.get = AsyncMock(return_value=None)
        ok = await check_quota_during_stream(uuid4(), 50, db=None)
        assert ok is True


# ── Storage 延迟初始化 ──

def test_storage_lazy_init():
    from app.services.storage import get_storage_service, _storage_service
    import app.services.storage as storage_mod
    storage_mod._storage_service = None
    s1 = get_storage_service()
    s2 = get_storage_service()
    assert s1 is s2
    storage_mod._storage_service = None
