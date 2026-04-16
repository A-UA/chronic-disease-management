"""向量数据库抽象接口"""
from __future__ import annotations

from typing import Any, Protocol


class SearchResult:
    """搜索结果标准结构"""
    __slots__ = ("id", "score", "payload")

    def __init__(self, id: int | str, score: float, payload: dict[str, Any]):
        self.id = id
        self.score = score
        self.payload = payload

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "score": self.score, "payload": self.payload}


class VectorStoreProtocol(Protocol):
    """向量数据库客户端协议"""

    async def insert(
        self,
        collection_name: str,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
    ) -> int:
        """插入向量和元数据，返回插入数量"""
        ...

    async def search(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """搜索最近邻，返回结果列表"""
        ...

    async def delete_by_document_id(
        self,
        collection_name: str,
        document_id: int,
    ) -> int:
        """按文档 ID 删除切块，返回删除数量"""
        ...

    async def ensure_collection(
        self,
        collection_name: str,
        dimension: int,
    ) -> None:
        """确保 collection 存在，不存在则创建"""
        ...
