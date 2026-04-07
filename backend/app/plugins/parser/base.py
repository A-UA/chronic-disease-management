"""文档解析器插件接口定义"""
from typing import Protocol
from dataclasses import dataclass


@dataclass(slots=True)
class ParseResult:
    """解析结果"""
    text: str
    pages: list[str]


class DocumentParseError(Exception):
    """文档解析错误"""
    pass


class ParserPlugin(Protocol):
    """文档解析器插件协议"""
    supported_types: list[str]
    def parse(self, file_bytes: bytes, filename: str) -> ParseResult: ...


def normalize_text(text: str) -> str:
    """标准化文本内容"""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    return normalized.strip()
