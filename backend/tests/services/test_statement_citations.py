from app.services.chat import build_statement_citations


def test_build_statement_citations_maps_doc_refs_to_citations():
    citations = [
        {"ref": "Doc 1", "doc_id": "doc-1", "chunk_id": "chunk-1", "page": 2, "chunk_index": 0, "snippet": "诊断：血糖升高。", "source_span": {"start": 0, "end": 8}},
        {"ref": "Doc 2", "doc_id": "doc-2", "chunk_id": "chunk-2", "page": 3, "chunk_index": 1, "snippet": "建议两周后复查。", "source_span": {"start": 0, "end": 8}},
    ]

    answer_text = "Conclusion: 建议继续监测血糖。[Doc 1]\nEvidence: 两周后复查空腹血糖。[Doc 2]"

    statements = build_statement_citations(answer_text, citations)

    assert len(statements) == 2
    assert statements[0]["text"].startswith("Conclusion:")
    assert statements[0]["citations"][0]["doc_id"] == "doc-1"
    assert statements[1]["citations"][0]["chunk_id"] == "chunk-2"
