from app.services.rag import split_document_text


def test_split_document_text_keeps_medical_heading_with_content():
    text = "主诉:\n反复头晕三天\n\n现病史:\n今晨加重"

    chunks = split_document_text(text)

    assert len(chunks) == 2
    assert chunks[0] == "主诉:\n反复头晕三天"
    assert chunks[1] == "现病史:\n今晨加重"


def test_split_document_text_splits_long_paragraphs():
    text = "a" * 1200

    chunks = split_document_text(text, chunk_size=500, chunk_overlap=100)

    assert len(chunks) == 3
    assert all(len(chunk) <= 500 for chunk in chunks)
    assert chunks[0][-100:] == chunks[1][:100]
