from pydantic_settings import BaseSettings

class AgentSettings(BaseSettings):
    GATEWAY_URL: str = "http://host.docker.internal:8080"
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION_PREFIX: str = "cdm_"
    CHAT_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-v4"
    
    # Langsmith config is automatically fetched from OS ENV by Langchain (LANGCHAIN_TRACING_V2, etc)
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = AgentSettings()
