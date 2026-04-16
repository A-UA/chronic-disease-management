# 第一期-子计划A：Agent 重构 + 基础设施 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将原 `backend/` 完全重构为纯 AI 中间层 `agent/`，接入 Milvus 向量数据库，暴露 6 个内部 HTTP 接口，删除所有业务模块。

**Architecture:** 原 `backend/` 重命名为 `agent/`，删除所有业务代码（routers/services/repositories/models/schemas/base），仅保留 AI 核心模块（rag/graph/plugins/tasks）。RAG 检索引擎从 SQLAlchemy+pgvector 重构为 Milvus 客户端。新增 `/internal/*` 内部 API 供 Java/NestJS 调用。

**Tech Stack:** Python 3.10+, FastAPI, pymilvus, arq, pydantic-settings

**设计文档:** `docs/superpowers/specs/2026-04-16-microservice-architecture-design.md`

---

## 文件结构

### 新建文件

| 文件 | 职责 |
|------|------|
| `agent/app/config.py` | Agent 专属配置（Milvus、LLM、Redis、MinIO） |
| `agent/app/main.py` | FastAPI 入口（仅 `/internal/*` 路由） |
| `agent/app/schemas/internal.py` | 内部 API 请求/响应模型 |
| `agent/app/vectorstore/base.py` | 向量数据库抽象接口（Protocol） |
| `agent/app/vectorstore/milvus.py` | Milvus 实现 |
| `agent/app/routers/internal.py` | `/internal/*` 6 个端点 |
| `agent/pyproject.toml` | 精简后的依赖（移除业务依赖，新增 pymilvus） |
| `agent/.env.example` | Agent 环境变量模板 |
| `database/alembic.ini` | Alembic 配置（从 agent 中移出） |
| `database/seed.py` | 种子数据脚本（从 agent 中移出） |

### 重构文件

| 文件 | 变更内容 |
|------|---------|
| `agent/app/rag/retrieval.py` | 移除 SQLAlchemy/pgvector，改用 Milvus 客户端检索 |
| `agent/app/rag/ingestion.py` | 移除 Chunk ORM，改为写入 Milvus |
| `agent/app/graph/*` | 从 `ai/agent/` 移入，修复导入路径 |
| `agent/app/plugins/registry.py` | 保留，修复导入路径 |
| `docker-compose.yml` | PostgreSQL 切换为标准版，新增 Milvus 服务 |

### 删除目录/文件

| 路径 | 原因 |
|------|------|
| `agent/app/routers/` (原业务路由) | 由 Java/NestJS 实现 |
| `agent/app/services/` | 由 Java/NestJS 实现 |
| `agent/app/repositories/` | 由 Java/NestJS 实现 |
| `agent/app/models/` | 由 Java/NestJS 实现 |
| `agent/app/schemas/` (原业务模型) | 重建为仅内部 API 模型 |
| `agent/app/base/` | 重建为轻量配置 |
| `agent/app/telemetry/` | 按需从零引入 |
| `agent/app/seed.py` | 迁移至 `database/` |
| `agent/alembic/` | 迁移至 `database/` |

---

## Task 1: 重命名 backend → agent 并清理目录

**Files:**
- Rename: `backend/` → `agent/`
- Delete: `agent/app/routers/`, `agent/app/services/`, `agent/app/repositories/`, `agent/app/models/`, `agent/app/schemas/`, `agent/app/base/`, `agent/app/telemetry/`, `agent/app/seed.py`
- Move: `agent/alembic/` → `database/alembic/`, `agent/alembic.ini` → `database/alembic.ini`

- [ ] **Step 1: 重命名 backend 目录为 agent**

```powershell
cd d:\codes\chronic-disease-management
git mv backend agent
```

- [ ] **Step 2: 删除所有业务模块目录**

```powershell
cd d:\codes\chronic-disease-management
Remove-Item -Recurse -Force agent/app/routers
Remove-Item -Recurse -Force agent/app/services
Remove-Item -Recurse -Force agent/app/repositories
Remove-Item -Recurse -Force agent/app/models
Remove-Item -Recurse -Force agent/app/schemas
Remove-Item -Recurse -Force agent/app/base
Remove-Item -Recurse -Force agent/app/telemetry
Remove-Item -Force agent/app/seed.py
```

- [ ] **Step 3: 迁移 alembic 和 seed 到 database 目录**

```powershell
cd d:\codes\chronic-disease-management
New-Item -ItemType Directory -Path database -Force
git mv agent/alembic database/alembic
git mv agent/alembic.ini database/alembic.ini
```

- [ ] **Step 4: 移动 AI 模块到新位置（消除 ai/ 嵌套）**

```powershell
cd d:\codes\chronic-disease-management
# ai/rag/ → rag/
git mv agent/app/ai/rag agent/app/rag
# ai/agent/ → graph/
git mv agent/app/ai/agent agent/app/graph
# 删除空的 ai 目录
Remove-Item -Recurse -Force agent/app/ai
```

- [ ] **Step 5: 提交目录重组**

```powershell
cd d:\codes\chronic-disease-management
git add -A
git commit -m "refactor: 重命名 backend → agent，删除业务模块，扁平化 AI 目录结构"
```

---

## Task 2: 创建 Agent 配置与依赖

**Files:**
- Create: `agent/app/config.py`
- Create: `agent/app/__init__.py`
- Overwrite: `agent/pyproject.toml`
- Create: `agent/.env.example`

- [ ] **Step 1: 创建 Agent 配置文件**

```python
# agent/app/config.py
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
```

- [ ] **Step 2: 精简 pyproject.toml（移除业务依赖，新增 pymilvus）**

```toml
# agent/pyproject.toml
[project]
name = "cdm-agent"
version = "0.1.0"
description = "AI Agent middleware for chronic disease management"
requires-python = ">=3.10"
dependencies = [
    # Web 框架
    "fastapi>=0.135.1",
    "uvicorn>=0.41.0",
    "orjson>=3.11.7",
    "python-multipart>=0.0.22",

    # 向量数据库
    "pymilvus>=2.4.0",

    # AI / LLM
    "openai>=2.29.0",
    "langgraph>=1.1.6",
    "tiktoken>=0.12.0",

    # 文档解析
    "pymupdf>=1.27.2.2",
    "pdfplumber>=0.11.9",
    "pytesseract>=0.3.13",

    # 配置与工具
    "pydantic-settings>=2.13.1",
    "redis>=7.3.0",
    "tenacity>=9.1.4",

    # 异步任务
    "arq>=0.25.0",

    # 对象存储（读取待解析文件）
    "aioboto3>=13.0.0",
]

[dependency-groups]
dev = [
    "httpx>=0.28.1",
    "pytest>=9.0.2",
    "pytest-asyncio>=1.3.0",
    "ruff>=0.15.9",
]

[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B"]
ignore = ["E501"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

- [ ] **Step 3: 创建 .env.example**

```env
# agent/.env.example

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_URL=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# LLM (OpenAI-compatible)
LLM_BASE_URL=
LLM_API_KEY=
CHAT_MODEL=gpt-4o-mini

# Embedding
EMBEDDING_BASE_URL=
EMBEDDING_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
```

- [ ] **Step 4: 创建 app/__init__.py**

```python
# agent/app/__init__.py
```

- [ ] **Step 5: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add -A
git commit -m "feat(agent): 创建 Agent 专属配置与精简依赖"
```

---

## Task 3: 实现 Milvus 向量数据库客户端

**Files:**
- Create: `agent/app/vectorstore/__init__.py`
- Create: `agent/app/vectorstore/base.py`
- Create: `agent/app/vectorstore/milvus.py`
- Test: `agent/tests/test_vectorstore.py`

- [ ] **Step 1: 编写向量数据库客户端的测试**

```python
# agent/tests/test_vectorstore.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class FakeMilvusResult:
    """模拟 Milvus 搜索结果"""
    def __init__(self, hits):
        self._hits = hits

    def __iter__(self):
        return iter(self._hits)

    def __len__(self):
        return len(self._hits)


class FakeHit:
    def __init__(self, id, distance, entity):
        self.id = id
        self.distance = distance
        self.entity = entity


@pytest.mark.asyncio
async def test_milvus_insert_vectors():
    """测试向量插入时正确调用 Milvus insert"""
    with patch("agent.app.vectorstore.milvus.MilvusClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.insert.return_value = {"insert_count": 2}

        from agent.app.vectorstore.milvus import MilvusVectorStore
        store = MilvusVectorStore(host="localhost", port=19530, collection_prefix="test")

        result = await store.insert(
            collection_name="test_kb_1",
            vectors=[[0.1, 0.2], [0.3, 0.4]],
            payloads=[
                {"document_id": 1, "content": "测试内容1", "chunk_index": 0},
                {"document_id": 1, "content": "测试内容2", "chunk_index": 1},
            ],
        )
        assert result == 2
        mock_client.insert.assert_called_once()


@pytest.mark.asyncio
async def test_milvus_search():
    """测试向量搜索返回正确结构"""
    with patch("agent.app.vectorstore.milvus.MilvusClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client

        mock_client.search.return_value = [[
            {"id": 1, "distance": 0.95, "entity": {"content": "结果1", "document_id": 10}},
            {"id": 2, "distance": 0.80, "entity": {"content": "结果2", "document_id": 10}},
        ]]

        from agent.app.vectorstore.milvus import MilvusVectorStore
        store = MilvusVectorStore(host="localhost", port=19530, collection_prefix="test")

        results = await store.search(
            collection_name="test_kb_1",
            vector=[0.1, 0.2],
            limit=5,
        )
        assert len(results) == 2
        assert results[0]["score"] == 0.95
        assert results[0]["payload"]["content"] == "结果1"


@pytest.mark.asyncio
async def test_milvus_delete_by_document_id():
    """测试按 document_id 删除切块"""
    with patch("agent.app.vectorstore.milvus.MilvusClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.delete.return_value = {"delete_count": 5}

        from agent.app.vectorstore.milvus import MilvusVectorStore
        store = MilvusVectorStore(host="localhost", port=19530, collection_prefix="test")

        count = await store.delete_by_document_id(
            collection_name="test_kb_1",
            document_id=123,
        )
        assert count == 5
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
cd d:\codes\chronic-disease-management\agent
uv run pytest tests/test_vectorstore.py -v
```

Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现向量数据库抽象接口**

```python
# agent/app/vectorstore/__init__.py
```

```python
# agent/app/vectorstore/base.py
"""向量数据库抽象接口"""
from __future__ import annotations

from typing import Any, Protocol


class SearchResult:
    """搜索结果标准结构"""
    __slots__ = ("id", "score", "payload")

    def __init__(self, id: int | str, score: float, payload: dict[str, Any]):
        self.id = id
        self.score = score
        self.payload = payload

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "score": self.score, "payload": self.payload}


class VectorStoreProtocol(Protocol):
    """向量数据库客户端协议"""

    async def insert(
        self,
        collection_name: str,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
    ) -> int:
        """插入向量和元数据，返回插入数量"""
        ...

    async def search(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """搜索最近邻，返回结果列表"""
        ...

    async def delete_by_document_id(
        self,
        collection_name: str,
        document_id: int,
    ) -> int:
        """按文档 ID 删除切块，返回删除数量"""
        ...

    async def ensure_collection(
        self,
        collection_name: str,
        dimension: int,
    ) -> None:
        """确保 collection 存在，不存在则创建"""
        ...
```

- [ ] **Step 4: 实现 Milvus 客户端**

```python
# agent/app/vectorstore/milvus.py
"""Milvus 向量数据库客户端实现"""
from __future__ import annotations

import logging
from typing import Any

from pymilvus import MilvusClient, DataType, CollectionSchema, FieldSchema

logger = logging.getLogger(__name__)


class MilvusVectorStore:
    """Milvus 向量数据库封装，实现 VectorStoreProtocol"""

    def __init__(self, host: str, port: int, collection_prefix: str = "cdm"):
        self._client = MilvusClient(uri=f"http://{host}:{port}")
        self._prefix = collection_prefix

    def _full_name(self, name: str) -> str:
        return f"{self._prefix}_{name}"

    async def ensure_collection(self, collection_name: str, dimension: int) -> None:
        """确保 collection 存在"""
        full_name = self._full_name(collection_name)
        if self._client.has_collection(full_name):
            return

        schema = CollectionSchema(fields=[
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            FieldSchema(name="document_id", dtype=DataType.INT64),
            FieldSchema(name="chunk_index", dtype=DataType.INT32),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="page_number", dtype=DataType.INT32),
            FieldSchema(name="token_count", dtype=DataType.INT32),
            FieldSchema(name="section_title", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="tenant_id", dtype=DataType.INT64),
            FieldSchema(name="kb_id", dtype=DataType.INT64),
        ])
        self._client.create_collection(
            collection_name=full_name,
            schema=schema,
        )
        # 创建向量索引
        self._client.create_index(
            collection_name=full_name,
            field_name="vector",
            index_params={"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 128}},
        )
        # 创建 document_id 标量索引（用于删除）
        self._client.create_index(
            collection_name=full_name,
            field_name="document_id",
        )
        logger.info("Created Milvus collection: %s (dim=%d)", full_name, dimension)

    async def insert(
        self,
        collection_name: str,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
    ) -> int:
        """插入向量+元数据"""
        full_name = self._full_name(collection_name)
        data = []
        for vec, payload in zip(vectors, payloads):
            row = {"vector": vec, **payload}
            data.append(row)

        result = self._client.insert(collection_name=full_name, data=data)
        count = result.get("insert_count", len(vectors))
        return count

    async def search(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """向量检索"""
        full_name = self._full_name(collection_name)
        filter_expr = ""
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, int):
                    conditions.append(f"{key} == {value}")
                elif isinstance(value, list):
                    conditions.append(f"{key} in {value}")
            filter_expr = " and ".join(conditions)

        results = self._client.search(
            collection_name=full_name,
            data=[vector],
            limit=limit,
            filter=filter_expr if filter_expr else None,
            output_fields=["document_id", "content", "chunk_index", "page_number",
                          "token_count", "section_title", "tenant_id", "kb_id"],
        )

        parsed = []
        for hits in results:
            for hit in hits:
                parsed.append({
                    "id": hit["id"],
                    "score": hit["distance"],
                    "payload": hit["entity"],
                })
        return parsed

    async def delete_by_document_id(
        self,
        collection_name: str,
        document_id: int,
    ) -> int:
        """按 document_id 删除所有切块"""
        full_name = self._full_name(collection_name)
        result = self._client.delete(
            collection_name=full_name,
            filter=f"document_id == {document_id}",
        )
        return result.get("delete_count", 0)
```

- [ ] **Step 5: 运行测试确认通过**

```powershell
cd d:\codes\chronic-disease-management\agent
uv run pytest tests/test_vectorstore.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 6: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add -A
git commit -m "feat(agent): 实现 Milvus 向量数据库客户端与抽象接口"
```

---

## Task 4: 创建内部 API 模型与路由

**Files:**
- Create: `agent/app/schemas/__init__.py`
- Create: `agent/app/schemas/internal.py`
- Create: `agent/app/routers/__init__.py`
- Create: `agent/app/routers/internal.py`

- [ ] **Step 1: 创建内部 API 请求/响应模型**

```python
# agent/app/schemas/__init__.py
```

```python
# agent/app/schemas/internal.py
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
```

- [ ] **Step 2: 创建内部路由骨架（6 个端点）**

```python
# agent/app/routers/__init__.py
```

```python
# agent/app/routers/internal.py
"""Agent 内部 API — 仅供 Java/NestJS 业务后端调用"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agent.app.schemas.internal import (
    IngestRequest, IngestResponse,
    DeleteChunksRequest, DeleteChunksResponse,
    ChatRequest, ChatSyncResponse,
    CompressRequest, CompressResponse,
    HealthResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(req: IngestRequest) -> IngestResponse:
    """文档切块 + Embedding + 写入 Milvus"""
    # TODO(Task 5): 对接 RAG ingestion pipeline
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete("/chunks", response_model=DeleteChunksResponse)
async def delete_chunks(req: DeleteChunksRequest) -> DeleteChunksResponse:
    """按文档 ID 删除 Milvus 中的切块"""
    # TODO(Task 5): 对接 Milvus 删除
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/chat")
async def chat_stream(req: ChatRequest):
    """RAG 检索 + LLM 对话（SSE 流式）"""
    # TODO(Task 6): 对接 RAG retrieval + LLM streaming
    async def event_generator():
        yield 'event: done\ndata: {}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/chat/sync", response_model=ChatSyncResponse)
async def chat_sync(req: ChatRequest) -> ChatSyncResponse:
    """RAG 检索 + LLM 对话（同步模式）"""
    # TODO(Task 6): 对接 RAG retrieval + LLM sync
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/compress", response_model=CompressResponse)
async def compress_history(req: CompressRequest) -> CompressResponse:
    """对话历史压缩"""
    # TODO(Task 6): 对接 compress 模块
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """健康检查"""
    return HealthResponse(status="ok")
```

- [ ] **Step 3: 创建 Agent FastAPI 入口**

```python
# agent/app/main.py
"""Agent AI 中间层 — FastAPI 入口"""
import logging

from fastapi import FastAPI

from agent.app.config import settings
from agent.app.routers.internal import router as internal_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CDM Agent - AI Middleware",
    description="内部 AI 中间层服务，仅供业务后端调用",
    version="0.1.0",
)

# 注册插件（延迟导入）
import importlib as _importlib
for _plugin in ("llm", "embedding", "reranker", "parser", "chunker"):
    try:
        _importlib.import_module(f"agent.app.plugins.{_plugin}")
    except ImportError:
        logger.warning("Plugin %s not found, skipping", _plugin)

# 挂载内部路由
app.include_router(internal_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
```

- [ ] **Step 4: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add -A
git commit -m "feat(agent): 创建内部 API 路由骨架与请求响应模型"
```

---

## Task 5: 更新 docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: 更新 Docker 配置**

将 `docker-compose.yml` 整体替换为以下内容：

```yaml
# docker-compose.yml
version: '3.8'

services:
  # ── 业务数据库（标准版，不含 pgvector）──
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ai_saas
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # ── 缓存 ──
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # ── 对象存储 ──
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  # ── Milvus 向量数据库（Standalone 模式）──
  milvus-etcd:
    image: quay.io/coreos/etcd:v3.5.16
    environment:
      ETCD_AUTO_COMPACTION_MODE: revision
      ETCD_AUTO_COMPACTION_RETENTION: "1000"
      ETCD_QUOTA_BACKEND_BYTES: "4294967296"
      ETCD_SNAPSHOT_COUNT: "50000"
    volumes:
      - milvus_etcd:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd

  milvus-minio:
    image: minio/minio
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - milvus_minio:/minio_data
    command: minio server /minio_data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  milvus:
    image: milvusdb/milvus:v2.4-latest
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: milvus-etcd:2379
      MINIO_ADDRESS: milvus-minio:9000
    ports:
      - "19530:19530"
      - "9091:9091"
    volumes:
      - milvus_data:/var/lib/milvus
    depends_on:
      - milvus-etcd
      - milvus-minio

volumes:
  postgres_data:
  minio_data:
  milvus_etcd:
  milvus_minio:
  milvus_data:
```

- [ ] **Step 2: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add docker-compose.yml
git commit -m "infra: PostgreSQL 切换为标准版，新增 Milvus standalone 服务"
```

---

## Task 6: 前端切换机制

**Files:**
- Modify: `frontend/apps/website/vite.config.ts`
- Create: `frontend/apps/website/.env.development`

- [ ] **Step 1: 添加前端环境变量**

```env
# frontend/apps/website/.env.development
VITE_BACKEND=java
```

- [ ] **Step 2: 更新 Vite 配置支持动态代理**

```typescript
// frontend/apps/website/vite.config.ts
import { defineConfig } from "vite-plus";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "path";

const backendPortMap: Record<string, number> = {
  java: 8000,
  nestjs: 8001,
};

const backend = process.env.VITE_BACKEND || "java";
const backendPort = backendPortMap[backend] || 8000;

export default defineConfig({
  staged: {
    "*": "vp check --fix",
  },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 3: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add -A
git commit -m "feat(frontend): 支持通过 VITE_BACKEND 环境变量切换 Java/NestJS 后端"
```

---

## 自审检查

1. **设计文档覆盖**：Task 1-6 覆盖了设计文档第一期的 P1-1（Agent 重构）、P1-2（Milvus 接入，docker-compose）、P1-3（内部接口骨架）、P1-6（前端切换）。P1-4 和 P1-5（Java/NestJS auth-service）将在后续子计划中覆盖。
2. **占位符扫描**：Task 4 中的路由为骨架实现，使用 `raise HTTPException(501)` 作为显式未实现标记，后续 Task 或第三期计划中填充。
3. **类型一致性**：`IngestRequest.document_id` (int) 贯穿 schemas、routers、vectorstore，类型一致。
4. **无遗漏**：RAG 引擎的 Milvus 重构（`retrieval.py`、`ingestion.py` 的内部改写）属于第三期（AI 对话链路），不在本子计划范围内。本计划的目标是让 Agent 能启动、能响应健康检查、骨架接口可用。
