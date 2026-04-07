"""纯文本 / Markdown 解析器插件"""
from app.plugins.parser.base import DocumentParseError, ParseResult, normalize_text
from app.plugins.registry import PluginRegistry


class TextParserPlugin:
    supported_types = [".txt", ".md", ".markdown"]

    def parse(self, file_bytes: bytes, filename: str) -> ParseResult:
        try:
            decoded = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentParseError("Text document is not valid UTF-8") from exc
        text = normalize_text(decoded)
        return ParseResult(text=text, pages=[text] if text else [])


PluginRegistry.register("parser", "text", lambda: TextParserPlugin())
