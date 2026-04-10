import logging

from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.base.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """Embedding provider 基类，所有方法均为异步"""

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError

    def get_dimension(self) -> int | None:
        return None


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """基于 AsyncOpenAI 的异步 Embedding Provider，兼容所有 OpenAI-compatible 厂商"""

    def __init__(self, client: AsyncOpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
        self._dimension: int | None = None

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self.client.embeddings.create(
                model=self.model_name, input=texts
            )
            embeddings = [item.embedding for item in response.data]
            if embeddings and self._dimension is None:
                self._dimension = len(embeddings[0])
            return embeddings
        except Exception as e:
            logger.error(f"Embedding batch failed: {str(e)}")
            raise

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=5),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def embed_query(self, text: str) -> list[float]:
        if not text:
            return []
        try:
            response = await self.client.embeddings.create(
                model=self.model_name, input=text
            )
            embedding = response.data[0].embedding
            if self._dimension is None:
                self._dimension = len(embedding)
            return embedding
        except Exception as e:
            logger.error(f"Embedding query failed: {str(e)}")
            raise

    def get_dimension(self) -> int | None:
        return self._dimension


def get_embedding_provider() -> EmbeddingProvider:
    """
    配置驱动的 Embedding Provider 工厂。

    所有 OpenAI-compatible 厂商（OpenAI / 智谱 / 通义千问 / DeepSeek 等）
    均通过 BASE_URL + API_KEY + MODEL 三个配置接入，无需修改代码。

    配置回退链：EMBEDDING_* → LLM_*（共享配置）
    """
    api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
    base_url = settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL

    if not api_key:
        raise ValueError("请设置 EMBEDDING_API_KEY（或 LLM_API_KEY 作为回退）")
    if not base_url:
        raise ValueError(
            "请设置 EMBEDDING_BASE_URL（或 LLM_BASE_URL 作为回退）。"
            "常见厂商地址参考 .env.example"
        )

    logger.info(
        "Embedding Provider: model=%s, base_url=%s", settings.EMBEDDING_MODEL, base_url
    )
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return OpenAIEmbeddingProvider(client, model_name=settings.EMBEDDING_MODEL)
