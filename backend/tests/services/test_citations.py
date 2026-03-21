from types import SimpleNamespace
from uuid import uuid4

from app.services.chat import build_rag_prompt


def test_build_rag_prompt_returns_chunk_level_citations():
    chunk = SimpleNamespace(
        id=uuid4(),
        document_id=uuid4(),
        page_number=5,
        chunk_index=7,
        content="诊断：空腹血糖升高。建议两周后复查，并记录饮食变化。",
    )

    _, citations = build_rag_prompt("血糖高怎么办？", [chunk])

    assert citations[0]["chunk_id"] == str(chunk.id)
    assert citations[0]["chunk_index"] == 7
    assert citations[0]["page"] == 5
    assert citations[0]["snippet"].startswith("诊断：空腹血糖升高")
    assert citations[0]["source_span"] == {"start": 0, "end": len(citations[0]["snippet"])}
