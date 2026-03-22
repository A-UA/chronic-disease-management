from typing import Optional

from app.core.config import settings
from app.services.embeddings import get_embedding_provider, EmbeddingProvider
from app.services.llm import get_llm_provider, LLMProvider
from app.services.reranker import get_reranker_provider, RerankerProvider

class ProviderRegistry:
    _instance = None
    
    def __init__(self):
        self.llm: Optional[LLMProvider] = None
        self.embedding: Optional[EmbeddingProvider] = None
        self.reranker: Optional[RerankerProvider] = None

    @classmethod
    def get_instance(cls) -> "ProviderRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self):
        self.llm = get_llm_provider()
        self.embedding = get_embedding_provider()
        self.reranker = get_reranker_provider()

    def get_llm(self) -> LLMProvider:
        if self.llm is None:
            self.llm = get_llm_provider()
        return self.llm

    def get_embedding(self) -> EmbeddingProvider:
        if self.embedding is None:
            self.embedding = get_embedding_provider()
        return self.embedding

    def get_reranker(self) -> RerankerProvider:
        if self.reranker is None:
            self.reranker = get_reranker_provider()
        return self.reranker

registry = ProviderRegistry.get_instance()
