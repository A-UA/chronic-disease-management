"""Document Parser 测试"""
import pytest
from app.services.document_parser import parse_document, DocumentParseError


def test_parse_txt():
    r = parse_document(b"hello world", "test.txt", "text/plain")
    assert r.text == "hello world"
    assert r.pages == ["hello world"]


def test_parse_unsupported():
    with pytest.raises(DocumentParseError, match="Unsupported"):
        parse_document(b"data", "test.xyz", None)


def test_parse_empty_txt():
    r = parse_document(b"   ", "test.txt", "text/plain")
    assert r.text == ""
    assert r.pages == []


def test_parse_docx():
    from io import BytesIO
    from zipfile import ZipFile

    buf = BytesIO()
    with ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')
        z.writestr("word/document.xml", '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body><w:p><w:r><w:t>诊断记录</w:t></w:r></w:p></w:body>
</w:document>''')

    r = parse_document(buf.getvalue(), "test.docx", None)
    assert "诊断记录" in r.text


def test_parse_txt_by_suffix_only():
    """通过文件后缀名识别，无需 content_type"""
    r = parse_document(b"content", "data.txt", None)
    assert r.text == "content"
