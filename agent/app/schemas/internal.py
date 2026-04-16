"""Agent 内部 API 请求/响应模型"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── 文档入库 ──


class IngestRequest(BaseModel):
    document_id: int
    kb_id: int
    file_url: str
    file_name: str
    tenant_id: int


class IngestResponse(BaseModel):
    status: str
    chunk_count: int
    token_count: int


# ── 删除切块 ──


class DeleteChunksRequest(BaseModel):
    document_id: int
    kb_id: int


class DeleteChunksResponse(BaseModel):
    deleted_count: int


# ── RAG 对话 ──


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatConfig(BaseModel):
    top_k: int = 5
    temperature: float = 0.7


class ChatRequest(BaseModel):
    query: str
    kb_ids: list[int]
    history: list[ChatMessage] = Field(default_factory=list)
    tenant_id: int
    config: ChatConfig = Field(default_factory=ChatConfig)


class ChatSyncResponse(BaseModel):
    answer: str
    citations: list[dict]
    usage: dict


# ── 对话压缩 ──


class CompressRequest(BaseModel):
    messages: list[ChatMessage]
    max_tokens: int = 500


class CompressResponse(BaseModel):
    compressed: str


# ── 健康检查 ──


class HealthResponse(BaseModel):
    status: str
    milvus: str = "ok"
    redis: str = "ok"
