from app.services.rag_ingestion import split_document_text


def test_split_document_text_keeps_common_medical_headings():
    text = "主诉:\n反复头晕三天\n\n现病史:\n今晨加重"

    chunks = split_document_text(text)

    assert chunks == ["主诉:\n反复头晕三天", "现病史:\n今晨加重"]


def test_split_document_text_supports_full_width_colon_headings():
    text = "诊断：\n2型糖尿病\n\n建议：\n规律复诊"

    chunks = split_document_text(text)

    assert chunks == ["诊断：\n2型糖尿病", "建议：\n规律复诊"]


def test_split_document_text_merges_heading_with_following_paragraph_after_blank_line():
    text = "主诉:\n\n反复头晕三天\n\n现病史:\n\n今晨加重"

    chunks = split_document_text(text)

    assert chunks == ["主诉:\n反复头晕三天", "现病史:\n今晨加重"]
