"""LLM 插件接口定义"""
from typing import Protocol
from collections.abc import AsyncGenerator


class LLMPlugin(Protocol):
    model_name: str
    async def stream_text(self, prompt: str) -> AsyncGenerator[str, None]: ...
    async def complete_text(self, prompt: str) -> str: ...
