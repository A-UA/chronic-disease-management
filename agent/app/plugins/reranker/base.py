"""Reranker 插件接口定义"""

from collections.abc import Sequence
from typing import Any, Protocol


class RerankerPlugin(Protocol):
    async def rerank(
        self, query: str, results: Sequence[Any], limit: int
    ) -> list[Any]: ...
