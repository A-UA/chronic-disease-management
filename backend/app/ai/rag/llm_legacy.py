import logging
from collections.abc import AsyncGenerator
from typing import Protocol

from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(Protocol):
    model_name: str

    async def stream_text(self, prompt: str) -> AsyncGenerator[str, None]: ...
    async def complete_text(self, prompt: str) -> str: ...


class OpenAICompatibleLLMProvider:
    def __init__(self, client: AsyncOpenAI, model_name: str):
        self.client = client
        self.model_name = model_name

    # 注意：流式输出通常在迭代过程中处理重试较复杂，这里主要对初始请求进行重试
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def stream_text(self, prompt: str) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            async for chunk in stream:
                text = None
                if chunk.choices:
                    text = chunk.choices[0].delta.content
                if text:
                    yield text
        except Exception as e:
            logger.error(f"LLM streaming failed: {str(e)}")
            raise

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def complete_text(self, prompt: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            if not response.choices:
                return ""
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM completion failed: {str(e)}")
            raise


def get_llm_provider() -> LLMProvider:
    """
    配置驱动的 LLM Provider 工厂。

    所有 OpenAI-compatible 厂商均通过 LLM_BASE_URL + LLM_API_KEY + CHAT_MODEL 接入。
    """
    if not settings.LLM_API_KEY:
        raise ValueError("请设置 LLM_API_KEY")
    if not settings.LLM_BASE_URL:
        raise ValueError("请设置 LLM_BASE_URL。常见厂商地址参考 .env.example")

    logger.info("LLM Provider: model=%s, base_url=%s", settings.CHAT_MODEL, settings.LLM_BASE_URL)
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
    return OpenAICompatibleLLMProvider(client, model_name=settings.CHAT_MODEL)
