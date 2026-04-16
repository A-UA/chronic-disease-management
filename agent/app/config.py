from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Agent AI 中间层配置 — 不包含任何业务配置（JWT、数据库等）"""

    # ── Milvus 向量数据库 ──
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION_PREFIX: str = "cdm"

    # ── Redis（缓存检索结果）──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── MinIO（读取待解析的文档文件）──
    MINIO_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "documents"

    # ── LLM ──
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    CHAT_MODEL: str = "gpt-4o-mini"

    # ── Embedding ──
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_BATCH_SIZE: int = 10

    # ── Reranker ──
    RERANKER_PROVIDER: str = "noop"
    RERANKER_BASE_URL: str = ""
    RERANKER_API_KEY: str = ""
    RERANKER_MODEL: str = ""

    # ── RAG 检索参数 ──
    RAG_VECTOR_WEIGHT: float = 0.7
    RAG_KEYWORD_WEIGHT: float = 0.3
    RAG_RRF_K: int = 60
    RAG_MIN_SCORE_THRESHOLD: float = 0.0
    RAG_CACHE_TTL: int = 3600
    RAG_ENABLE_CONTEXTUAL_INGESTION: bool = False

    # ── arq Worker ──
    ARQ_MAX_JOBS: int = 10
    ARQ_JOB_TIMEOUT: int = 600

    # ── 服务端口 ──
    HOST: str = "0.0.0.0"
    PORT: int = 8100

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = AgentSettings()
