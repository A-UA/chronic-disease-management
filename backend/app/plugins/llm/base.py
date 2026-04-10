"""LLM 插件接口定义"""

from collections.abc import AsyncGenerator
from typing import Protocol


class LLMPlugin(Protocol):
    model_name: str

    async def stream_text(self, prompt: str) -> AsyncGenerator[str, None]: ...
    async def complete_text(self, prompt: str) -> str: ...
