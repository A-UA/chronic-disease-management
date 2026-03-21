from app.services.rag_evaluation import evaluate_rag_cases


def test_evaluate_rag_cases_returns_extended_metrics():
    cases = [
        {
            "id": "case-1",
            "expected_chunk_ids": ["a"],
            "retrieved_chunk_ids": ["a"],
            "expected_answer_keywords": ["复查"],
            "answer_text": "建议复查。",
            "expected_citation_doc_ids": ["doc-1"],
            "citation_doc_ids": ["doc-1"],
            "expected_refusal": False,
            "refusal": False,
            "latency_ms": 800,
            "total_tokens": 120,
        },
        {
            "id": "case-2",
            "expected_chunk_ids": ["x"],
            "retrieved_chunk_ids": ["y"],
            "expected_answer_keywords": ["不知道"],
            "answer_text": "不知道。",
            "expected_citation_doc_ids": [],
            "citation_doc_ids": [],
            "expected_refusal": True,
            "refusal": True,
            "latency_ms": 1200,
            "total_tokens": 80,
        },
    ]

    summary = evaluate_rag_cases(cases, k=1)

    assert summary["metrics"]["refusal_match_rate"] == 1.0
    assert summary["metrics"]["avg_latency_ms"] == 1000.0
    assert summary["metrics"]["avg_total_tokens"] == 100.0
