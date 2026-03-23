"""Query rewrite / conversation context / embedding validation 测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.query_rewrite import prepare_retrieval_query, normalize_query, rewrite_query
from app.services.conversation_context import (
    build_retrieval_query_from_history,
    is_likely_follow_up,
)
from app.services.embedding_validation import validate_embedding_provider


# ── Query Rewrite ──

def test_normalize_query():
    assert normalize_query("  血糖高怎么办？\n\n  ") == "血糖高怎么办?"


def test_rewrite_exact_match():
    assert rewrite_query("这个药还要继续吃吗") == "用药是否需要继续"


def test_rewrite_unknown_keeps_original():
    q = "今天天气怎么样"
    assert "今天天气怎么样" in rewrite_query(q)


def test_prepare_retrieval_query_normalizes():
    p = prepare_retrieval_query("  血糖高？  ")
    assert p.original_query == "  血糖高？  "
    assert p.normalized_query == "血糖高?"


def test_medical_synonym_expansion():
    p = prepare_retrieval_query("糖尿病怎么治")
    assert "血糖异常" in p.retrieval_query or "DM" in p.retrieval_query


# ── Conversation Context ──

def test_follow_up_detected():
    assert is_likely_follow_up("那这个药还要吃吗") is True
    assert is_likely_follow_up("继续") is True


def test_standalone_question_not_follow_up():
    assert is_likely_follow_up("高血压患者应该如何监测血压？") is False


def test_build_query_expands_follow_up():
    q = build_retrieval_query_from_history(
        "那这个药还要继续吃吗？",
        [{"role": "user", "content": "2型糖尿病怎么办"}, {"role": "assistant", "content": "ok"}],
    )
    assert "2型糖尿病怎么办" in q
    assert "这个药还要继续吃吗" in q


def test_build_query_standalone_unchanged():
    q = build_retrieval_query_from_history(
        "高血压患者应该如何监测血压？",
        [{"role": "user", "content": "xx"}],
    )
    assert "高血压患者应该如何监测血压" in q


def test_build_query_no_history():
    q = build_retrieval_query_from_history("hello?", [])
    assert q == "hello?"


# ── Embedding Validation ──

@pytest.mark.asyncio
async def test_validate_ok():
    p = MagicMock()
    p.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
    r = await validate_embedding_provider(p, "test")
    assert r["ok"] is True
    assert r["vector_length"] == 3


@pytest.mark.asyncio
async def test_validate_fail():
    p = MagicMock()
    p.embed_query = AsyncMock(side_effect=RuntimeError("nope"))
    r = await validate_embedding_provider(p, "test")
    assert r["ok"] is False
    assert "nope" in r["error"]
