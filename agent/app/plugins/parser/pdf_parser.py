"""PDF 文档解析器插件 — PyMuPDF 主解析 + pdfplumber OCR 回退"""

import logging
from io import BytesIO

import fitz  # PyMuPDF
import pdfplumber
import pytesseract

from app.plugins.parser.base import DocumentParseError, ParseResult, normalize_text
from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


class PdfParserPlugin:
    supported_types = [".pdf"]

    def parse(self, file_bytes: bytes, filename: str) -> ParseResult:
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

            # 文本极少时回退到 OCR
            if total_text_length < 50 and len(pages) > 0:
                logger.info("PDF has very little text, falling back to OCR")
                pages = []
                with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if not text or len(text.strip()) < 50:
                            pil_image = page.to_image(resolution=300).original
                            text = pytesseract.image_to_string(
                                pil_image, lang="chi_sim+eng"
                            )
                        pages.append(text.strip() if text else "")

            pages = [p for p in pages if p]
            if not pages:
                raise DocumentParseError("PDF document contains no extractable text")

            combined = normalize_text("\n\n".join(pages))
            return ParseResult(text=combined, pages=pages)
        except Exception as e:
            if isinstance(e, DocumentParseError):
                raise
            logger.error(f"Failed to parse PDF: {str(e)}")
            raise DocumentParseError(f"PDF parsing error: {str(e)}")


PluginRegistry.register("parser", "pdf", lambda: PdfParserPlugin())
