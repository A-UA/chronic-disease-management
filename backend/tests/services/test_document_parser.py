import pytest

from app.services.document_parser import DocumentParseError, parse_document


def test_parse_text_document_normalizes_bom_and_newlines():
    parsed = parse_document(
        b"\xef\xbb\xbfline1\r\nline2\rline3",
        filename="note.txt",
        content_type="text/plain",
    )

    assert parsed.text == "line1\nline2\nline3"
    assert parsed.pages == ["line1\nline2\nline3"]


def test_parse_document_rejects_unsupported_binary_type():
    with pytest.raises(DocumentParseError, match="Unsupported document type"):
        parse_document(
            b"%PDF-1.4 binary data",
            filename="report.pdf",
            content_type="application/pdf",
        )


def test_parse_document_uses_filename_when_content_type_missing():
    parsed = parse_document(
        b"hello world",
        filename="summary.txt",
        content_type=None,
    )

    assert parsed.text == "hello world"
