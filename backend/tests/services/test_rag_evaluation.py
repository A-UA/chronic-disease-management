"""RAG 评测服务测试"""
import pytest
from app.modules.rag.evaluation import _has_keyword_match, evaluate_rag_cases


class TestHasKeywordMatch:
    def test_all_keywords_present(self):
        assert _has_keyword_match("高血压需要服用降压药", ["高血压", "降压药"]) is True

    def test_partial_keywords_missing(self):
        assert _has_keyword_match("高血压需要治疗", ["高血压", "降压药"]) is False

    def test_empty_keywords(self):
        """空关键词列表应视为匹配"""
        assert _has_keyword_match("任意文本", []) is True

    def test_empty_answer(self):
        assert _has_keyword_match("", ["关键词"]) is False


class TestEvaluateRagCases:
    @pytest.mark.asyncio
    async def test_empty_cases(self):
        """空用例列表应返回 case_count=0"""
        result = await evaluate_rag_cases([])
        assert result["case_count"] == 0
        assert result["metrics"] == {}
        assert result["cases"] == []

    @pytest.mark.asyncio
    async def test_retrieval_recall(self):
        """检索召回率计算"""
        cases = [
            {
                "id": 1,
                "query": "高血压",
                "answer_text": "高血压需要药物治疗",
                "expected_answer": "",
                "expected_chunk_ids": [101, 102],
                "retrieved_chunk_ids": [101, 103, 104],
                "expected_answer_keywords": ["药物"],
                "expected_citation_doc_ids": [],
                "citation_doc_ids": [],
            }
        ]
        result = await evaluate_rag_cases(cases, k=5)
        assert result["case_count"] == 1
        assert result["metrics"]["recall_at_k"] == 1.0  # 101 命中
        assert result["metrics"]["keyword_match_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_latency_aggregation(self):
        """延迟统计应正确聚合"""
        cases = [
            {"id": 1, "query": "q1", "answer_text": "a1", "expected_answer": "",
             "expected_chunk_ids": [], "retrieved_chunk_ids": [],
             "latency_ms": 100, "total_tokens": 50},
            {"id": 2, "query": "q2", "answer_text": "a2", "expected_answer": "",
             "expected_chunk_ids": [], "retrieved_chunk_ids": [],
             "latency_ms": 200, "total_tokens": 150},
        ]
        result = await evaluate_rag_cases(cases)
        assert result["metrics"]["avg_latency_ms"] == 150.0
        assert result["metrics"]["avg_total_tokens"] == 100.0
