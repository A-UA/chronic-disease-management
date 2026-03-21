from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


@dataclass(slots=True)
class ParsedDocument:
    text: str
    pages: list[str]


class DocumentParseError(Exception):
    pass


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    return normalized.strip()


def _parse_text_document(file_bytes: bytes) -> ParsedDocument:
    try:
        decoded = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentParseError("Text document is not valid UTF-8") from exc

    text = _normalize_text(decoded)
    return ParsedDocument(text=text, pages=[text] if text else [])


def _parse_docx_document(file_bytes: bytes) -> ParsedDocument:
    try:
        with ZipFile(BytesIO(file_bytes)) as archive:
            document_xml = archive.read("word/document.xml")
    except KeyError as exc:
        raise DocumentParseError("DOCX document is missing word/document.xml") from exc
    except BadZipFile as exc:
        raise DocumentParseError("DOCX document is invalid or corrupted") from exc

    root = ElementTree.fromstring(document_xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:body/w:p", namespace):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        combined = "".join(texts).strip()
        if combined:
            paragraphs.append(combined)

    text = _normalize_text("\n\n".join(paragraphs))
    return ParsedDocument(text=text, pages=[text] if text else [])


def _decode_pdf_literal_string(raw: str) -> str:
    return (
        raw.replace(r"\(", "(")
        .replace(r"\)", ")")
        .replace(r"\n", "\n")
        .replace(r"\r", "\r")
        .replace(r"\t", "\t")
        .replace(r"\\", "\\")
    )


def _parse_pdf_document(file_bytes: bytes) -> ParsedDocument:
    text = file_bytes.decode("latin-1", errors="ignore")
    streams = re.findall(r"stream\s*(.*?)\s*endstream", text, flags=re.DOTALL)

    pages: list[str] = []
    for stream in streams:
        blocks = re.findall(r"BT(.*?)ET", stream, flags=re.DOTALL)
        for block in blocks:
            lines: list[str] = []
            for raw_text in re.findall(r"\((.*?)(?<!\\)\)\s*Tj", block, flags=re.DOTALL):
                decoded = _decode_pdf_literal_string(raw_text).strip()
                if decoded:
                    lines.append(decoded)

            if lines:
                pages.append("\n".join(lines))

    if not pages:
        raise DocumentParseError("PDF document contains no extractable text")

    combined = _normalize_text("\n\n".join(pages))
    return ParsedDocument(text=combined, pages=pages)


def parse_document(file_bytes: bytes, filename: str, content_type: str | None) -> ParsedDocument:
    suffix = Path(filename).suffix.lower()
    normalized_content_type = (content_type or "").split(";")[0].strip().lower()

    if suffix == ".txt" or normalized_content_type == "text/plain":
        return _parse_text_document(file_bytes)

    if suffix == ".docx" or normalized_content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _parse_docx_document(file_bytes)

    if suffix == ".pdf" or normalized_content_type == "application/pdf":
        return _parse_pdf_document(file_bytes)

    raise DocumentParseError(f"Unsupported document type: {suffix or normalized_content_type or 'unknown'}")
