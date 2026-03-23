"""RAG 评测测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rag_evaluation import evaluate_rag_cases


@pytest.mark.asyncio
async def test_evaluate_empty():
    r = await evaluate_rag_cases([])
    assert r["case_count"] == 0
    assert r["metrics"] == {}


@pytest.mark.asyncio
async def test_evaluate_basic_metrics():
    cases = [
        {
            "id": "c1",
            "query": "血糖高怎么办",
            "answer_text": "建议复查空腹血糖",
            "expected_answer": "",
            "expected_chunk_ids": ["ch1", "ch2"],
            "retrieved_chunk_ids": ["ch1", "ch3"],
            "expected_answer_keywords": ["复查"],
            "expected_citation_doc_ids": ["d1"],
            "citation_doc_ids": ["d1"],
            "latency_ms": 200,
            "total_tokens": 500,
        }
    ]

    with patch("app.services.rag_evaluation.registry.get_llm") as mock_get_llm:
        llm = MagicMock()
        llm.complete_text = AsyncMock(return_value='{"correct": true}')
        mock_get_llm.return_value = llm
        r = await evaluate_rag_cases(cases)

    assert r["case_count"] == 1
    m = r["metrics"]
    assert m["recall_at_k"] == 1.0
    assert m["keyword_match_rate"] == 1.0
    assert m["citation_hit_rate"] == 1.0
    assert m["avg_latency_ms"] == 200.0


@pytest.mark.asyncio
async def test_evaluate_refusal_match():
    cases = [
        {
            "id": "c1",
            "query": "q",
            "answer_text": "a",
            "expected_answer": "",
            "expected_chunk_ids": [],
            "retrieved_chunk_ids": [],
            "expected_refusal": True,
            "refusal": True,
        }
    ]
    with patch("app.services.rag_evaluation.registry.get_llm") as mock_get_llm:
        llm = MagicMock()
        llm.complete_text = AsyncMock(return_value='{"correct": false}')
        mock_get_llm.return_value = llm
        r = await evaluate_rag_cases(cases)

    assert r["metrics"]["refusal_match_rate"] == 1.0
