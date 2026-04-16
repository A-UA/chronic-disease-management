from __future__ import annotations

from types import SimpleNamespace


def test_build_rag_prompt_returns_citations_and_redacts_patient_name() -> None:
    from app.ai.rag.prompt import build_rag_prompt

    chunks = [
        SimpleNamespace(
            id=101,
            document_id=201,
            page_number=3,
            content="张三今日血压 140/90，建议复查。",
        ),
    ]

    prompt, citations = build_rag_prompt(
        query="张三的血压情况是什么？",
        chunks=chunks,
        patient_name="张三",
    )

    assert "[Doc 1]" in prompt
    assert "[PATIENT]" in prompt
    assert "张三" not in prompt
    assert citations == [
        {
            "doc_id": "201",
            "chunk_id": "101",
            "ref": "Doc 1",
            "page": 3,
            "snippet": "[PATIENT]今日血压 140/90，建议复查。",
            "source_span": {"start": 0, "end": 26},
        }
    ]
