import pytest
from zipfile import ZipFile
from io import BytesIO

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
            b"\x89PNG\r\n\x1a\n",
            filename="image.png",
            content_type="image/png",
        )


def test_parse_document_uses_filename_when_content_type_missing():
    parsed = parse_document(
        b"hello world",
        filename="summary.txt",
        content_type=None,
    )

    assert parsed.text == "hello world"


def test_parse_docx_document_extracts_text():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
            </Types>""",
        )
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:body>
                    <w:p><w:r><w:t>第一段</w:t></w:r></w:p>
                    <w:p><w:r><w:t>第二段</w:t></w:r></w:p>
                </w:body>
            </w:document>""",
        )

    parsed = parse_document(
        buffer.getvalue(),
        filename="summary.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert parsed.text == "第一段\n\n第二段"
    assert parsed.pages == ["第一段\n\n第二段"]


def test_parse_pdf_document_extracts_text_from_simple_pdf():
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 55 >> stream\n"
        b"BT /F1 12 Tf 72 100 Td (PDF first line) Tj T* (PDF second line) Tj ET\n"
        b"endstream endobj\n"
        b"trailer << /Root 1 0 R >>\n"
        b"%%EOF"
    )

    parsed = parse_document(
        pdf_bytes,
        filename="report.pdf",
        content_type="application/pdf",
    )

    assert parsed.text == "PDF first line\nPDF second line"
    assert parsed.pages == ["PDF first line\nPDF second line"]
