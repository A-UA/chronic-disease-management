import logging
from typing import Any

from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError

    def get_dimension(self) -> int | None:
        return None


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
        self._dimension: int | None = None

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = self.client.embeddings.create(model=self.model_name, input=texts)
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
    def embed_query(self, text: str) -> list[float]:
        if not text:
            return []
        try:
            response = self.client.embeddings.create(model=self.model_name, input=text)
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
    provider_name = settings.EMBEDDING_PROVIDER.lower().strip()
    api_key = settings.EMBEDDING_API_KEY or settings.OPENAI_API_KEY or settings.LLM_API_KEY
    base_url = settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL

    if provider_name == "openai":
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        client = OpenAI(api_key=api_key, base_url=base_url or "https://api.openai.com/v1")
        return OpenAIEmbeddingProvider(client, model_name=settings.EMBEDDING_MODEL)

    if provider_name == "zhipu":
        if not api_key:
            raise ValueError("EMBEDDING_API_KEY is required when EMBEDDING_PROVIDER=zhipu")
        # 智谱默认 base_url
        client = OpenAI(api_key=api_key, base_url=base_url or "https://open.bigmodel.cn/api/paas/v4/")
        return OpenAIEmbeddingProvider(client, model_name=settings.EMBEDDING_MODEL)

    raise ValueError(f"Unsupported embedding provider: {settings.EMBEDDING_PROVIDER}")
