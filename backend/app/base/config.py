from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Multi-Tenant AI SaaS"
    API_V1_STR: str = "/api/v1"
    DEBUG_SQL: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_saas"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    # MinIO
    MINIO_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "documents"

    # Security — 必须通过 .env 或环境变量显式设置，禁止使用默认值
    JWT_SECRET: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    API_KEY_SALT: str = ""  # 用于API密钥哈希的盐值

    # Upload
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── AI 通用配置（LLM / Embedding / Reranker 共享的回退配置）──
    LLM_BASE_URL: str = ""      # OpenAI-compatible 服务地址（必填）
    LLM_API_KEY: str = ""       # 对应厂商的 API Key（必填）
    CHAT_MODEL: str = "gpt-4o-mini"

    # ── Embedding（留空则回退到 LLM_* 配置）──
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_BATCH_SIZE: int = 10  # 单次 Embedding API 最大文本数（通义千问=10, OpenAI=2048）

    # ── Reranker（provider 决定实现类：noop / simple / 其他为 OpenAI-compatible）──
    RERANKER_PROVIDER: str = "noop"
    RERANKER_BASE_URL: str = ""
    RERANKER_API_KEY: str = ""
    RERANKER_MODEL: str = ""

    # RAG 检索参数
    RAG_VECTOR_WEIGHT: float = 0.7  # 向量检索在 RRF 融合中的权重
    RAG_KEYWORD_WEIGHT: float = 0.3  # 关键词检索在 RRF 融合中的权重
    RAG_RRF_K: int = 60  # RRF 融合参数 k
    RAG_MIN_SCORE_THRESHOLD: float = 0.0  # 检索结果最低分数阈值
    RAG_CACHE_TTL: int = 3600  # 检索缓存 TTL（秒）
    RAG_ENABLE_CONTEXTUAL_INGESTION: bool = False  # 是否开启入库背景增强（消耗额外 Token）

    # SMTP 邮件（可选，未配置时验证码仅输出到日志）
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_TLS: bool = False  # True=STARTTLS, False=SSL

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # OpenTelemetry
    OTLP_ENDPOINT: str = ""
    OTEL_SERVICE_NAME: str = "cdm-backend"

    # arq Worker
    ARQ_MAX_JOBS: int = 10
    ARQ_JOB_TIMEOUT: int = 600


    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @model_validator(mode="after")
    def validate_jwt_secret(self):
        if not self.JWT_SECRET:
            raise ValueError("FATAL: JWT_SECRET 必须通过 .env 或环境变量显式设置")
        if not self.API_KEY_SALT:
            raise ValueError("FATAL: API_KEY_SALT 必须通过 .env 或环境变量显式设置")
        return self


settings = Settings()
