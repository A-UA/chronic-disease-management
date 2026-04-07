"""切块策略插件接口定义"""
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ChunkResult:
    """切块结果"""
    content: str
    page_number: int | None
    section_title: str | None
    char_start: int
    char_end: int


class ChunkerPlugin(Protocol):
    """切块策略插件协议"""
    name: str
    def chunk(self, text: str, pages: list[str] | None = None,
              chunk_size: int = 800, chunk_overlap: int = 150) -> list[ChunkResult]: ...
