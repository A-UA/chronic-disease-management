from __future__ import annotations

import json
import logging
from typing import Any

from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)

def _has_keyword_match(answer_text: str, expected_keywords: list[str]) -> bool:
    if not expected_keywords:
        return True
    return all(keyword in answer_text for keyword in expected_keywords)

async def _llm_judge_correctness(query: str, answer: str, expected_answer: str) -> bool:
    """使用 LLM 作为裁判，判断回答是否与参考答案一致"""
    llm = PluginRegistry.get("llm")
    prompt = (
        "You are an expert medical auditor. Compare the generated answer with the reference answer for the given query.\n"
        "Judge if the generated answer is factually correct and consistent with the reference.\n"
        f"Query: {query}\n"
        f"Generated Answer: {answer}\n"
        f"Reference Answer: {expected_answer}\n\n"
        "Return strict JSON: {\"correct\": true/false, \"reason\": \"...\"}"
    )

    try:
        response = await llm.complete_text(prompt)
        # 尝试提取 JSON
        if "{" in response:
            data = json.loads(response[response.find("{"):response.rfind("}")+1])
            return bool(data.get("correct", False))
    except Exception as e:
        logger.warning(f"LLM Judge failed: {str(e)}")
    return False

async def evaluate_rag_cases(cases: list[dict[str, Any]], k: int = 5) -> dict[str, Any]:
    evaluated_cases = []
    retrieval_hits = 0
    answer_hits = 0
    llm_judge_hits = 0
    citation_hits = 0
    refusal_hits = 0
    latency_values: list[float] = []
    total_token_values: list[float] = []

    for case in cases:
        query = case.get("query", "")
        answer_text = case.get("answer_text", "")
        expected_answer = case.get("expected_answer", "")

        # 1. 检索召回率 (Recall@K)
        expected_chunk_ids = set(case.get("expected_chunk_ids", []))
        retrieved_chunk_ids = case.get("retrieved_chunk_ids", [])[:k]
        retrieval_hit = bool(expected_chunk_ids.intersection(retrieved_chunk_ids))
        if retrieval_hit:
            retrieval_hits += 1

        # 2. 基础关键词匹配
        answer_hit = _has_keyword_match(answer_text, case.get("expected_answer_keywords", []))
        if answer_hit:
            answer_hits += 1

        # 3. LLM 裁判 (Correctness)
        judge_hit = False
        if expected_answer and answer_text:
            judge_hit = await _llm_judge_correctness(query, answer_text, expected_answer)
            if judge_hit:
                llm_judge_hits += 1

        # 4. 引用准确率
        expected_citation_doc_ids = set(case.get("expected_citation_doc_ids", []))
        citation_doc_ids = set(case.get("citation_doc_ids", []))
        citation_hit = citation_doc_ids == expected_citation_doc_ids
        if citation_hit:
            citation_hits += 1

        # 5. 拒答准确率
        expected_refusal = case.get("expected_refusal")
        actual_refusal = case.get("refusal")
        refusal_hit = expected_refusal == actual_refusal if expected_refusal is not None else True
        if refusal_hit:
            refusal_hits += 1

        # 6. Query Condensation
        expected_condensed = case.get("expected_condensed_query")
        actual_condensed = case.get("condensed_query")
        condensation_hit = True
        if expected_condensed:
            condensation_hit = (expected_condensed.lower() == (actual_condensed or "").lower())

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
                "llm_judge_hit": judge_hit,
                "citation_hit": citation_hit,
                "refusal_hit": refusal_hit,
                "condensation_hit": condensation_hit,
            }
        )

    case_count = len(cases)
    if case_count == 0:
        return {
            "case_count": 0,
            "metrics": {},
            "cases": [],
        }

    condensation_hits = sum(1 for c in evaluated_cases if c["condensation_hit"])

    return {
        "case_count": case_count,
        "metrics": {
            "recall_at_k": round(retrieval_hits / case_count, 4),
            "keyword_match_rate": round(answer_hits / case_count, 4),
            "llm_judge_accuracy": round(llm_judge_hits / case_count, 4),
            "citation_hit_rate": round(citation_hits / case_count, 4),
            "refusal_match_rate": round(refusal_hits / case_count, 4),
            "query_condensation_score": round(condensation_hits / case_count, 4),
            "avg_latency_ms": round(sum(latency_values) / len(latency_values), 4) if latency_values else 0.0,
            "avg_total_tokens": round(sum(total_token_values) / len(total_token_values), 4) if total_token_values else 0.0,
        },
        "cases": evaluated_cases,
    }
