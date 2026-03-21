import pytest

from app.services.chat import extract_statement_citations_structured


class DummyLLM:
    async def complete_text(self, prompt: str) -> str:
        return (
            '{"statements":['
            '{"text":"Conclusion: 建议复查。","refs":["Doc 1"]},'
            '{"text":"Evidence: 两周后复查。","refs":["Doc 2"]}'
            "]}"
        )


@pytest.mark.asyncio
async def test_extract_statement_citations_structured_uses_llm_json_mapping():
    citations = [
        {"ref": "Doc 1", "doc_id": "doc-1", "chunk_id": "chunk-1", "page": 2, "chunk_index": 0, "snippet": "诊断：血糖升高。", "source_span": {"start": 0, "end": 8}},
        {"ref": "Doc 2", "doc_id": "doc-2", "chunk_id": "chunk-2", "page": 3, "chunk_index": 1, "snippet": "建议两周后复查。", "source_span": {"start": 0, "end": 8}},
    ]

    statements = await extract_statement_citations_structured(
        "Conclusion: 建议复查。\nEvidence: 两周后复查。",
        citations,
        DummyLLM(),
    )

    assert len(statements) == 2
    assert statements[0]["citations"][0]["doc_id"] == "doc-1"
    assert statements[1]["citations"][0]["chunk_id"] == "chunk-2"
