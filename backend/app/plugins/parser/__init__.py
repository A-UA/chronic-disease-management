"""文档解析器插件包"""
from app.plugins.parser.base import ParseResult, DocumentParseError, ParserPlugin, normalize_text  # noqa: F401
import app.plugins.parser.text_parser  # noqa: F401 — 触发注册
import app.plugins.parser.docx_parser  # noqa: F401
import app.plugins.parser.pdf_parser  # noqa: F401
