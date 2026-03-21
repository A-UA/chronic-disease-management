from types import SimpleNamespace
from uuid import uuid4

from app.services.chat import build_rag_prompt


def test_build_rag_prompt_includes_structured_answer_requirements_and_snippet_citations():
    chunk = SimpleNamespace(
        document_id=uuid4(),
        page_number=3,
        content="诊断：2 型糖尿病。建议一周后复查空腹血糖并继续监测饮食。",
    )

    prompt, citations = build_rag_prompt("血糖高怎么办？", [chunk], patient_name=None)

    assert "Answer format:" in prompt
    assert "1. Conclusion" in prompt
    assert "2. Evidence" in prompt
    assert "3. Uncertainty" in prompt
    assert citations[0]["snippet"].startswith("诊断：2 型糖尿病")
    assert citations[0]["page"] == 3
