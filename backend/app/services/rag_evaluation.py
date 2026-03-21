from __future__ import annotations

from typing import Any


def _has_keyword_match(answer_text: str, expected_keywords: list[str]) -> bool:
    if not expected_keywords:
        return True
    return all(keyword in answer_text for keyword in expected_keywords)


def evaluate_rag_cases(cases: list[dict[str, Any]], k: int = 5) -> dict[str, Any]:
    evaluated_cases = []
    retrieval_hits = 0
    answer_hits = 0
    citation_hits = 0

    for case in cases:
        expected_chunk_ids = set(case.get("expected_chunk_ids", []))
        retrieved_chunk_ids = case.get("retrieved_chunk_ids", [])[:k]
        retrieval_hit = bool(expected_chunk_ids.intersection(retrieved_chunk_ids))
        if retrieval_hit:
            retrieval_hits += 1

        answer_hit = _has_keyword_match(case.get("answer_text", ""), case.get("expected_answer_keywords", []))
        if answer_hit:
            answer_hits += 1

        expected_citation_doc_ids = set(case.get("expected_citation_doc_ids", []))
        citation_doc_ids = set(case.get("citation_doc_ids", []))
        citation_hit = citation_doc_ids == expected_citation_doc_ids
        if citation_hit:
            citation_hits += 1

        evaluated_cases.append(
            {
                "id": case.get("id"),
                "retrieval_hit": retrieval_hit,
                "answer_hit": answer_hit,
                "citation_hit": citation_hit,
            }
        )

    case_count = len(cases)
    if case_count == 0:
        return {
            "case_count": 0,
            "metrics": {
                "recall_at_k": 0.0,
                "answer_match_rate": 0.0,
                "citation_hit_rate": 0.0,
            },
            "cases": [],
        }

    return {
        "case_count": case_count,
        "metrics": {
            "recall_at_k": round(retrieval_hits / case_count, 4),
            "answer_match_rate": round(answer_hits / case_count, 4),
            "citation_hit_rate": round(citation_hits / case_count, 4),
        },
        "cases": evaluated_cases,
    }
