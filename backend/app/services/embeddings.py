from openai import OpenAI

from app.core.config import settings


class EmbeddingProvider:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class MockEmbeddingProvider(EmbeddingProvider):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1536 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1] * 1536


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model_name, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model_name, input=text)
        return response.data[0].embedding


def get_embedding_provider() -> EmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == "openai":
        api_key = settings.EMBEDDING_API_KEY or settings.OPENAI_API_KEY or settings.LLM_API_KEY
        base_url = settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        return OpenAIEmbeddingProvider(client, model_name=settings.EMBEDDING_MODEL)

    return MockEmbeddingProvider()
