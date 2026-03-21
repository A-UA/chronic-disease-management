# Multi-Tenant AI SaaS 项目指南

更新时间：2026-03-22

## 1. 项目概览

本项目是一个以 RAG 为核心能力的多租户 AI SaaS 后端，当前重点建设方向是“文档入库 -> 检索 -> 引用化问答 -> 评测闭环”。

当前技术栈：

- 后端框架：FastAPI
- ORM：SQLAlchemy 2.x Async
- 数据库：PostgreSQL + pgvector
- 缓存与限流：Redis
- 对象存储：MinIO
- 测试：pytest / pytest-asyncio

当前 RAG 主链路：

- 文档解析：`backend/app/services/document_parser.py`
- 文档切块与入库：`backend/app/services/rag_ingestion.py`
- 检索与 Prompt：`backend/app/services/chat.py`
- 对话上下文处理：`backend/app/services/conversation_context.py`
- LLM provider：`backend/app/services/llm.py`
- Embedding provider：`backend/app/services/embeddings.py`
- Reranker provider：`backend/app/services/reranker.py`
- 离线评测：`backend/app/services/rag_evaluation.py`

## 2. 当前已落地的 RAG 能力

### 文档入库

- 支持 `txt`、基础 `docx`、基础文本型 `pdf`
- 上传链路已改为“先解析，再上传，再入库”
- 文档处理失败会写入 `failed_reason`
- `rag.py` 已降为兼容层，真实入库实现位于 `rag_ingestion.py`

### 检索链路

- 已支持 query 规范化和基础 rewrite
- 已支持基于最近会话消息构造 contextual retrieval query
- 已支持 hybrid retrieval + reranker 接口壳层
- 检索缓存已升级为结构化缓存，保留排序与分数
- 已支持 `document_ids`、`file_types` 两类 metadata filter

### 回答与引用

- 聊天接口已通过 provider 方式接入 LLM
- Prompt 已采用 `Conclusion / Evidence / Uncertainty` 结构
- citation 已包含 `doc_id`、`chunk_id`、`chunk_index`、`page`、`snippet`、`source_span`
- 已支持 `statement_citations`
- 已增加结构化 statement-citation 抽取，降低对模型内联 `[Doc n]` 的依赖

### 工程能力

- Storage 已改为延迟初始化：`get_storage_service()`
- Redis 已改为延迟初始化：`get_redis_client()`
- 流式配额检查在 Redis miss 时会回退数据库
- assistant message metadata 已增加 `observability`
- 离线评测已支持：
  - `recall_at_k`
  - `answer_match_rate`
  - `citation_hit_rate`
  - `refusal_match_rate`
  - `avg_latency_ms`
  - `avg_total_tokens`

## 3. 目录说明

- `backend/app/api/`: API 路由与依赖
- `backend/app/core/`: 配置与安全设置
- `backend/app/db/`: 数据库模型、会话、迁移
- `backend/app/services/`: 主要业务服务层
- `backend/alembic/`: Alembic 迁移
- `backend/tests/`: 自动化测试
- `backend/scripts/`: 辅助脚本
- `docs/`: 项目文档

重点文档：

- `docs/rag专项整改清单.md`

## 4. 本地开发

### 启动依赖

```bash
docker compose up -d
```

### 安装依赖

```bash
cd backend
uv sync
```

### 初始化数据库

```bash
uv run alembic upgrade head
```

### 启动服务

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 运行测试

```bash
uv run python -m pytest
```

## 5. 配置约定

主要环境变量位于 `backend/.env`，参考模板位于 `backend/.env.example`。

当前推荐配置方向：

- 聊天 / reranker：可使用 Xiaomi MiMo 的 OpenAI 兼容网关
- embeddings：MiMo 当前不支持本项目所需 embeddings 路径，需接真实可用的 embedding 服务

关键配置项：

- `LLM_PROVIDER`
- `CHAT_MODEL`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `RERANKER_PROVIDER`
- `RERANKER_MODEL`
- `RERANKER_API_KEY`
- `RERANKER_BASE_URL`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_BASE_URL`

## 6. 当前剩余重点

- 接入真实可用的 embedding provider
- 扩充离线评测样本并接入 CI
- 增加更细粒度的业务 filter
- 增强多轮对话压缩与专项评测
- 统一 LLM / embedding provider 生命周期管理

## 7. 开发约定

- 新增功能优先走 provider / service 抽象，不直接把外部依赖写死在 endpoint
- 检索行为变更优先补测试，再改实现
- 涉及 RAG 质量变更时，同步更新 `docs/rag专项整改清单.md`
- 不要在导入阶段初始化外部服务
