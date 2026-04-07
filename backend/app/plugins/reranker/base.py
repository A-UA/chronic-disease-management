"""Reranker 插件接口定义"""
from typing import Protocol, Any
from collections.abc import Sequence


class RerankerPlugin(Protocol):
    async def rerank(self, query: str, results: Sequence[Any], limit: int) -> list[Any]: ...
