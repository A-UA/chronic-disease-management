from app.services.rag_evaluation import evaluate_rag_cases


def test_evaluate_rag_cases_returns_basic_metrics():
    cases = [
        {
            "id": "case-1",
            "expected_chunk_ids": ["a", "b"],
            "retrieved_chunk_ids": ["b", "c"],
            "expected_answer_keywords": ["复查", "饮食"],
            "answer_text": "建议复查，并继续控制饮食。",
            "expected_citation_doc_ids": ["doc-1"],
            "citation_doc_ids": ["doc-1", "doc-2"],
        },
        {
            "id": "case-2",
            "expected_chunk_ids": ["x"],
            "retrieved_chunk_ids": ["y"],
            "expected_answer_keywords": ["不知道"],
            "answer_text": "不知道。",
            "expected_citation_doc_ids": ["doc-9"],
            "citation_doc_ids": [],
        },
    ]

    summary = evaluate_rag_cases(cases, k=2)

    assert summary["case_count"] == 2
    assert summary["metrics"]["recall_at_k"] == 0.5
    assert summary["metrics"]["answer_match_rate"] == 1.0
    assert summary["metrics"]["citation_hit_rate"] == 0.0
    assert summary["cases"][0]["retrieval_hit"] is True
    assert summary["cases"][0]["citation_hit"] is False
    assert summary["cases"][1]["citation_hit"] is False
