from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ParsedDocument:
    text: str
    pages: list[str]


class DocumentParseError(Exception):
    pass


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    return normalized.strip()


def parse_document(file_bytes: bytes, filename: str, content_type: str | None) -> ParsedDocument:
    suffix = Path(filename).suffix.lower()
    normalized_content_type = (content_type or "").split(";")[0].strip().lower()

    if suffix == ".txt" or normalized_content_type == "text/plain":
        try:
            decoded = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentParseError("Text document is not valid UTF-8") from exc

        text = _normalize_text(decoded)
        return ParsedDocument(text=text, pages=[text] if text else [])

    raise DocumentParseError(f"Unsupported document type: {suffix or normalized_content_type or 'unknown'}")
