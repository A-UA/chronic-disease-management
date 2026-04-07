import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

import fitz  # PyMuPDF
import pdfplumber
import pytesseract

logger = logging.getLogger(__name__)

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

    def _extract_text_recursive(element) -> list[str]:
        texts: list[str] = []
        for child in element:
            # 处理段落
            if child.tag.endswith("}p"):
                t_nodes = child.findall(".//w:t", namespace)
                p_text = "".join(node.text or "" for node in t_nodes).strip()
                if p_text:
                    texts.append(p_text)
            # 处理表格
            elif child.tag.endswith("}tbl"):
                table_texts: list[str] = []
                for row in child.findall(".//w:tr", namespace):
                    row_cells = []
                    for cell in row.findall(".//w:tc", namespace):
                        cell_text = " ".join(_extract_text_recursive(cell)).strip()
                        row_cells.append(cell_text)
                    if any(row_cells):
                        table_texts.append(" | ".join(row_cells))
                if table_texts:
                    texts.append("\n" + "\n".join(table_texts) + "\n")
            # 递归处理其他容器（如 body）
            elif child.tag.endswith("}body") or child.tag.endswith("}sdtContent"):
                texts.extend(_extract_text_recursive(child))
        return texts

    body = root.find("w:body", namespace)
    if body is None:
        return ParsedDocument(text="", pages=[])

    all_texts = _extract_text_recursive(body)
    text = _normalize_text("\n\n".join(all_texts))
    return ParsedDocument(text=text, pages=[text] if text else [])


def _parse_pdf_document(file_bytes: bytes) -> ParsedDocument:
    """专业 PDF 解析：使用 PyMuPDF (fitz) 处理排版与编码，低文字时回退到 OCR"""
    try:
        pages: list[str] = []
        total_text_length = 0

        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            if doc.is_encrypted:
                raise DocumentParseError("PDF document is encrypted")

            for page in doc:
                text = page.get_text("text").strip()
                pages.append(text)
                total_text_length += len(text)

        # If very little text was extracted, it might be a scanned PDF. Fallback to OCR.
        if total_text_length < 50 and len(pages) > 0:
            logger.info("PDF has very little text, falling back to OCR")
            pages = []
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    # Try layout-aware text extraction first
                    text = page.extract_text()

                    if not text or len(text.strip()) < 50:
                        # Fallback to image OCR
                        pil_image = page.to_image(resolution=300).original
                        text = pytesseract.image_to_string(pil_image, lang="chi_sim+eng")

                    pages.append(text.strip() if text else "")

        # Remove completely empty pages
        pages = [p for p in pages if p]

        if not pages:
            raise DocumentParseError("PDF document contains no extractable text")

        combined = _normalize_text("\n\n".join(pages))
        return ParsedDocument(text=combined, pages=pages)
    except Exception as e:
        if isinstance(e, DocumentParseError):
            raise
        logger.error(f"Failed to parse PDF: {str(e)}")
        raise DocumentParseError(f"PDF parsing error: {str(e)}")


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
