import asyncio
from collections.abc import AsyncGenerator
from typing import Protocol

from openai import AsyncOpenAI

from app.core.config import settings


class LLMProvider(Protocol):
    model_name: str

    async def stream_text(self, prompt: str) -> AsyncGenerator[str, None]: ...
    async def complete_text(self, prompt: str) -> str: ...


class MockLLMProvider:
    model_name = "gpt-4o-mock"

    async def stream_text(self, prompt: str) -> AsyncGenerator[str, None]:
        words = ["Here", " is", " a", " mocked", " response", " to", " your", " query."]
        for word in words:
            await asyncio.sleep(0.1)
            yield word

    async def complete_text(self, prompt: str) -> str:
        return '{"statements":[]}'


class OpenAICompatibleLLMProvider:
    def __init__(self, client: AsyncOpenAI, model_name: str):
        self.client = client
        self.model_name = model_name

    async def stream_text(self, prompt: str) -> AsyncGenerator[str, None]:
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

    async def complete_text(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        if not response.choices:
            return ""
        return response.choices[0].message.content or ""


def get_llm_provider() -> LLMProvider:
    provider_name = settings.LLM_PROVIDER.lower().strip()
    if provider_name in {"", "mock"}:
        return MockLLMProvider()

    if provider_name in {"openai_compatible", "xiaomi_mimo"}:
        if not settings.LLM_API_KEY:
            raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=openai_compatible")
        if not settings.LLM_BASE_URL:
            raise ValueError("LLM_BASE_URL is required when LLM_PROVIDER=openai_compatible")

        client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
        return OpenAICompatibleLLMProvider(client, model_name=settings.CHAT_MODEL)

    raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
