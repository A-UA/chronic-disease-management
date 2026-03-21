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
    refusal_hits = 0
    latency_values: list[float] = []
    total_token_values: list[float] = []

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

        expected_refusal = case.get("expected_refusal")
        actual_refusal = case.get("refusal")
        refusal_hit = expected_refusal == actual_refusal if expected_refusal is not None else True
        if refusal_hit:
            refusal_hits += 1

        latency_ms = case.get("latency_ms")
        if latency_ms is not None:
            latency_values.append(float(latency_ms))

        total_tokens = case.get("total_tokens")
        if total_tokens is not None:
            total_token_values.append(float(total_tokens))

        evaluated_cases.append(
            {
                "id": case.get("id"),
                "retrieval_hit": retrieval_hit,
                "answer_hit": answer_hit,
                "citation_hit": citation_hit,
                "refusal_hit": refusal_hit,
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
                "refusal_match_rate": 0.0,
                "avg_latency_ms": 0.0,
                "avg_total_tokens": 0.0,
            },
            "cases": [],
        }

    return {
        "case_count": case_count,
        "metrics": {
            "recall_at_k": round(retrieval_hits / case_count, 4),
            "answer_match_rate": round(answer_hits / case_count, 4),
            "citation_hit_rate": round(citation_hits / case_count, 4),
            "refusal_match_rate": round(refusal_hits / case_count, 4),
            "avg_latency_ms": round(sum(latency_values) / len(latency_values), 4) if latency_values else 0.0,
            "avg_total_tokens": round(sum(total_token_values) / len(total_token_values), 4) if total_token_values else 0.0,
        },
        "cases": evaluated_cases,
    }
