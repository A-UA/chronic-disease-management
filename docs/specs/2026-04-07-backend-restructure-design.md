# 后端系统性重构设计规格

> **状态**：已批准
> **日期**：2026-04-07
> **范围**：后端整体目录结构、项目架构、项目逻辑的系统性重构

---

## 1. 重构目标

### 1.1 核心问题

当前后端采用扁平的 `api/endpoints/ → services/ → db/models/` 三层结构，存在以下痛点：

| 问题 | 现状 | 影响 |
|------|------|------|
| **文档入库同步阻塞** | `rag_ingestion.py` 在 API 端点内 `await process_document()` | 大文件卡住请求 30 秒以上 |
| **零可观测性** | 仅有 `logging.getLogger` 原始日志 | RAG 管线各阶段耗时无法追踪，问题无法定位 |
| **业务逻辑混杂** | 20 个端点文件和 19 个服务文件堆在同级目录 | 文件间隐式依赖，改一处牵动全局 |
| **AI 能力硬编码** | Provider 切换需改代码 | 无法轻松实验新模型/新策略 |

### 1.2 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 架构风格 | 业务模块垂直切分 + AI 插件体系 | 比 DDD 直观，业务按模块隔离，AI 能力可插拔 |
| 异步任务 | arq（基于 Redis） | 已在依赖中，纯异步原生，与 FastAPI 天然配合 |
| 可观测性 | OpenTelemetry 链路追踪 + 结构化日志 | 行业标准，代码侵入性低 |
| 不采用 DDD | — | 团队规模和项目复杂度不需要聚合根、限界上下文等重概念 |

---

## 2. 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                      main.py                            │
│              FastAPI 应用 + 中间件注册                    │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────────┐
        ▼              ▼                  ▼
   ┌─────────┐   ┌──────────┐      ┌───────────┐
   │  core/  │   │ modules/ │      │ plugins/  │
   │ 基础设施 │   │ 业务模块  │      │ AI 插件   │
   └────┬────┘   └────┬─────┘      └─────┬─────┘
        │              │                  │
        │    ┌─────────┼─────────┐        │
        │    ▼         ▼         ▼        │
        │  auth    system     patient     │
        │  rag     agent      audit       │
        │              │                  │
        │              ▼                  │
        │    ┌───────────────────┐        │
        │    │     tasks/       │◄────────┘
        │    │   arq Worker     │
        │    └───────────────────┘
        │              │
        ▼              ▼
   ┌──────────┐  ┌────────────┐
   │   db/    │  │ telemetry/ │
   │ 数据层   │  │ 可观测性    │
   └──────────┘  └────────────┘
```

---

## 3. 目录结构

```
backend/app/
├── main.py                          # 应用入口，中间件注册
│
├── core/                            # 全局基础设施
│   ├── config.py                    # pydantic-settings 配置
│   ├── security.py                  # JWT、Argon2
│   ├── middleware.py                # X-Request-ID
│   ├── snowflake.py                 # 雪花 ID
│   ├── deps.py                      # 认证、RLS、权限校验等通用依赖
│   └── exceptions.py               # 统一异常定义
│
├── db/                              # 数据层（共享）
│   ├── base.py                      # Base、IDMixin、TimestampMixin
│   ├── session.py                   # AsyncSession 工厂
│   └── seed_data.py                 # 种子数据
│
├── modules/                         # ═══ 业务模块 ═══
│   │
│   ├── auth/                        # 认证模块
│   │   ├── __init__.py
│   │   ├── router.py                # /auth/*
│   │   ├── service.py               # 登录、注册、JWT 签发、密码重置
│   │   ├── schemas.py               # LoginRequest、TokenResponse...
│   │   └── models.py                # User、PasswordResetToken
│   │
│   ├── system/                      # 系统管理模块
│   │   ├── __init__.py
│   │   ├── router.py                # /organizations、/users、/rbac、/api-keys、/settings、/tenants、/menus
│   │   ├── service.py               # 组织、成员、角色权限
│   │   ├── schemas.py
│   │   ├── models.py                # Tenant、Organization、OrganizationUser、Role、Menu、ApiKey、SystemSetting...
│   │   └── quota.py                 # 配额管理
│   │
│   ├── patient/                     # 患者管理模块
│   │   ├── __init__.py
│   │   ├── router.py                # /patients、/health-metrics、/family、/managers
│   │   ├── service.py               # 患者档案、管理师分配
│   │   ├── schemas.py
│   │   ├── models.py                # PatientProfile、HealthMetric、ManagerProfile、PatientFamilyLink...
│   │   └── alert.py                 # 健康指标异常告警
│   │
│   ├── rag/                         # RAG 知识检索模块
│   │   ├── __init__.py
│   │   ├── router.py                # /chat、/kb、/documents、/conversations
│   │   ├── service.py               # 检索编排（调用 plugins）
│   │   ├── schemas.py               # ChatRequest、ChatResponse
│   │   ├── models.py                # KnowledgeBase、Document、Chunk、Conversation、Message、UsageLog
│   │   ├── ingestion.py             # 入库管线编排（Parser → Chunker → Embedding → Store）
│   │   ├── retrieval.py             # 检索管线编排（Rewrite → MultiQuery → Search → RRF → Rerank）
│   │   ├── citation.py              # 引用提取、声明级引用映射
│   │   ├── query_rewrite.py         # 医疗查询改写（同义词表 + 术语扩展）
│   │   ├── evaluation.py            # RAG 质量评测
│   │   ├── context.py               # 对话上下文增强与多轮压缩
│   │   └── tasks.py                 # ⭐ arq 异步任务（文档入库处理）
│   │
│   ├── agent/                       # Agent 智能体模块
│   │   ├── __init__.py              # run_agent 入口
│   │   ├── router.py                # Agent 模式路由（复用 /chat?use_agent=true）
│   │   ├── graph.py                 # LangGraph 图定义
│   │   ├── state.py                 # AgentState TypedDict
│   │   ├── memory.py                # 对话记忆增强
│   │   ├── security.py              # SecurityContext
│   │   └── skills/                  # Agent 技能
│   │       ├── __init__.py
│   │       ├── base.py              # SkillRegistry
│   │       ├── patient_skills.py    # 患者数据查询技能
│   │       ├── calculator_skills.py # BMI 等计算
│   │       └── rag_skill.py         # RAG 检索技能
│   │
│   └── audit/                       # 审计与统计模块
│       ├── __init__.py
│       ├── router.py                # /audit-logs、/usage、/dashboard、/external
│       ├── service.py               # 审计日志查询、使用量统计、仪表盘
│       ├── schemas.py
│       ├── models.py                # AuditLog
│       └── tasks.py                 # ⭐ 异步审计写入（fire_audit → arq）
│
├── plugins/                         # ═══ AI 可插拔能力 ═══
│   ├── __init__.py
│   ├── registry.py                  # 统一插件注册中心
│   │
│   ├── llm/                         # LLM 插件族
│   │   ├── __init__.py
│   │   ├── base.py                  # LLMPlugin Protocol
│   │   └── openai_compatible.py     # OpenAI 兼容实现（含重试）
│   │
│   ├── embedding/                   # Embedding 插件族
│   │   ├── __init__.py
│   │   ├── base.py                  # EmbeddingPlugin Protocol
│   │   └── openai_compatible.py
│   │
│   ├── reranker/                    # Reranker 插件族
│   │   ├── __init__.py
│   │   ├── base.py                  # RerankerPlugin Protocol
│   │   ├── noop.py                  # 不重排，直接截断
│   │   ├── simple.py                # 基于来源数量的加分重排
│   │   └── openai_compatible.py     # OpenAI 兼容 LLM 重排
│   │
│   ├── parser/                      # 文档解析插件族
│   │   ├── __init__.py
│   │   ├── base.py                  # ParserPlugin Protocol
│   │   ├── pdf_parser.py            # PyMuPDF + pdfplumber
│   │   └── markdown_parser.py       # Markdown 解析
│   │
│   └── chunker/                     # 切块策略插件族
│       ├── __init__.py
│       ├── base.py                  # ChunkerPlugin Protocol
│       ├── sentence_chunker.py      # 按句子边界 + Token 控制
│       └── medical_heading.py       # 医疗章节感知切块
│
├── tasks/                           # ⭐ 异步任务基础设施
│   ├── __init__.py
│   ├── worker.py                    # arq WorkerSettings（收集各模块任务）
│   └── registry.py                  # 任务函数注册表
│
└── telemetry/                       # ⭐ 可观测性
    ├── __init__.py
    ├── setup.py                     # OpenTelemetry SDK 初始化
    ├── tracing.py                   # Tracer 工具函数 + 装饰器
    └── logging.py                   # 结构化日志配置（structlog）
```

---

## 4. 核心设计细节

### 4.1 插件注册中心

```python
# plugins/registry.py
from typing import Any, Callable

class PluginRegistry:
    """统一插件注册中心

    特点：
    - 配置驱动：根据 settings 自动选择默认插件
    - 延迟初始化：首次 get() 时才创建实例
    - 工厂模式：注册的是工厂函数，不是实例
    """

    _factories: dict[str, dict[str, Callable]] = {}
    _instances: dict[str, dict[str, Any]] = {}

    @classmethod
    def register(cls, category: str, name: str, factory: Callable):
        cls._factories.setdefault(category, {})[name] = factory

    @classmethod
    def get(cls, category: str, name: str | None = None) -> Any:
        key = name or cls._resolve_default(category)
        instances = cls._instances.setdefault(category, {})
        if key not in instances:
            factory = cls._factories[category][key]
            instances[key] = factory()
        return instances[key]

    @classmethod
    def _resolve_default(cls, category: str) -> str:
        from app.core.config import settings
        defaults = {
            "llm": "openai_compatible",
            "embedding": "openai_compatible",
            "reranker": settings.RERANKER_PROVIDER or "noop",
            "parser": "pdf",
            "chunker": "medical_heading",
        }
        return defaults.get(category, "default")

    @classmethod
    def reset(cls):
        """测试用：清除所有缓存实例"""
        cls._instances.clear()
```

### 4.2 插件基类

```python
# plugins/llm/base.py
from typing import Protocol, AsyncGenerator

class LLMPlugin(Protocol):
    model_name: str
    async def stream_text(self, prompt: str) -> AsyncGenerator[str, None]: ...
    async def complete_text(self, prompt: str) -> str: ...
```

```python
# plugins/chunker/base.py
from typing import Protocol
from dataclasses import dataclass

@dataclass(slots=True)
class ChunkResult:
    content: str
    page_number: int | None
    section_title: str | None
    char_start: int
    char_end: int
    metadata: dict

class ChunkerPlugin(Protocol):
    name: str
    def chunk(self, text: str, pages: list[str] | None = None,
              chunk_size: int = 800, chunk_overlap: int = 150) -> list[ChunkResult]: ...
```

```python
# plugins/parser/base.py
from typing import Protocol
from dataclasses import dataclass

@dataclass(slots=True)
class ParseResult:
    text: str
    pages: list[str] | None
    metadata: dict

class ParserPlugin(Protocol):
    supported_types: list[str]
    def parse(self, file_content: bytes, file_name: str) -> ParseResult: ...
```

### 4.3 arq 异步任务体系

```python
# tasks/worker.py
from arq.connections import RedisSettings
from app.core.config import settings

async def startup(ctx):
    """Worker 启动时初始化"""
    pass

async def shutdown(ctx):
    """Worker 关闭时清理"""
    pass

class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    functions = []

    @classmethod
    def collect_functions(cls):
        from app.modules.rag.tasks import process_document_task
        from app.modules.audit.tasks import write_audit_log_task
        cls.functions = [process_document_task, write_audit_log_task]
```

```python
# modules/rag/tasks.py
from app.telemetry.tracing import trace_span

async def process_document_task(ctx, document_id: int, org_id: int):
    """异步文档入库任务"""
    with trace_span("task.process_document", attributes={"document_id": document_id}):
        from app.modules.rag.ingestion import IngestionPipeline
        pipeline = IngestionPipeline()
        await pipeline.run(document_id, org_id)
```

```python
# modules/audit/tasks.py
async def write_audit_log_task(ctx, tenant_id: int, user_id: int,
                                action: str, resource: str, detail: dict):
    """异步审计日志写入"""
    from app.db.session import AsyncSessionLocal
    from app.modules.audit.models import AuditLog
    async with AsyncSessionLocal() as db:
        log = AuditLog(
            tenant_id=tenant_id, user_id=user_id,
            action=action, resource=resource, detail=detail,
        )
        db.add(log)
        await db.commit()
```

### 4.4 OpenTelemetry 链路追踪

```python
# telemetry/setup.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def setup_telemetry(app):
    """初始化 OpenTelemetry（在 main.py 中调用）"""
    from app.core.config import settings
    provider = TracerProvider()
    if settings.OTLP_ENDPOINT:
        exporter = OTLPSpanExporter(endpoint=settings.OTLP_ENDPOINT)
        provider.add_span_processor(BatchSpanExporter(exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
```

```python
# telemetry/tracing.py
from contextlib import contextmanager
from opentelemetry import trace
from functools import wraps

tracer = trace.get_tracer("cdm.backend")

@contextmanager
def trace_span(name: str, attributes: dict | None = None):
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
        yield span

def traced(name: str | None = None):
    def decorator(func):
        span_name = name or f"{func.__module__}.{func.__qualname__}"
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with trace_span(span_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### 4.5 RAG 检索管线（加入追踪）

```python
# modules/rag/retrieval.py
from app.telemetry.tracing import trace_span, traced
from app.plugins.registry import PluginRegistry

class RetrievalPipeline:
    """检索管线：Rewrite → MultiQuery → Search → RRF → Rerank"""

    @traced("rag.retrieve")
    async def retrieve(self, db, query, kb_id, org_id, user_id,
                       limit=5, filters=None, history=None):
        with trace_span("rag.query_rewrite"):
            from app.modules.rag.query_rewrite import prepare_retrieval_query
            prepared = prepare_retrieval_query(query)

        with trace_span("rag.multi_query"):
            all_queries = await self._expand_queries(prepared.retrieval_query, history)

        with trace_span("rag.hybrid_search", {"query_count": len(all_queries)}):
            raw_results = await self._hybrid_search(
                db, all_queries, kb_id, org_id, limit, filters
            )

        with trace_span("rag.rrf_fusion"):
            fused = self._rrf_fuse(raw_results)

        with trace_span("rag.rerank"):
            reranker = PluginRegistry.get("reranker")
            final = await reranker.rerank(query, fused, limit)

        return final
```

### 4.6 入库管线（串联插件）

```python
# modules/rag/ingestion.py
from app.plugins.registry import PluginRegistry
from app.telemetry.tracing import trace_span, traced

class IngestionPipeline:
    """文档入库管线：Parser → Chunker → Embedding → Store"""

    @traced("rag.ingest")
    async def run(self, document_id: int, org_id: int):
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as db:
            await db.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"),
                {"org_id": str(org_id)},
            )
            document = await db.get(Document, document_id)
            if not document:
                return

            with trace_span("rag.parse", {"file_type": document.file_type}):
                parser = PluginRegistry.get("parser", document.file_type or "pdf")
                parse_result = parser.parse(document.raw_content, document.file_name)

            with trace_span("rag.chunk"):
                chunker = PluginRegistry.get("chunker")
                chunks = chunker.chunk(parse_result.text, parse_result.pages)

            with trace_span("rag.embed", {"chunk_count": len(chunks)}):
                embedder = PluginRegistry.get("embedding")
                contents = [c.content for c in chunks]
                vectors = await self._batch_embed(embedder, contents)

            with trace_span("rag.store"):
                await self._store_chunks(db, document, chunks, vectors)

            document.status = "completed"
            await db.commit()
```

---

## 5. 数据流变化

### 5.1 文档入库（同步 → 异步）

```
# ❌ 现在
POST /documents/upload
  → endpoint 内直接 await process_document()    ← 阻塞 30 秒+
  → 返回结果

# ✅ 重构后
POST /documents/upload
  → 文件上传到 MinIO + 创建 Document 记录（status="processing"）
  → await arq_pool.enqueue_job("process_document_task", doc_id, org_id)
  → 立即返回 {"status": "processing", "document_id": "..."}

GET /documents/{id}
  → 返回 {"status": "completed"} 或 {"status": "processing"}

arq Worker（独立进程）
  → 取到任务
  → [trace span] IngestionPipeline.run()
  → Parser 插件 → Chunker 插件 → Embedding 插件 → 写入 DB
  → 更新 document.status
```

### 5.2 RAG 检索（加入完整追踪链路）

```
POST /chat
  │ [trace: rag.chat_request]
  ├─ [span: rag.load_history]       → Token 预算动态加载历史
  ├─ [span: rag.context_enhance]    → 追问上下文增强
  ├─ [span: rag.retrieve]
  │   ├─ [span: rag.query_rewrite]  → 医疗同义词扩展
  │   ├─ [span: rag.multi_query]    → 查询扩展（复杂查询）
  │   ├─ [span: rag.hybrid_search]  → pgvector + tsv 并行检索
  │   ├─ [span: rag.rrf_fusion]     → RRF 融合
  │   └─ [span: rag.rerank]         → Reranker 插件
  ├─ [span: rag.prompt_build]       → RAG prompt 构建
  ├─ [span: rag.llm_stream]         → LLM 流式生成
  └─ [span: rag.citation_extract]   → 引用抽取
```

### 5.3 审计日志（同步 → 异步）

```
# ❌ 现在：fire_audit 用 asyncio.create_task（进程重启丢失）
# ✅ 重构后：投递到 arq 队列
async def fire_audit(tenant_id, user_id, action, resource, detail):
    await arq_pool.enqueue_job(
        "write_audit_log_task",
        tenant_id, user_id, action, resource, detail
    )
```

---

## 6. 模块间依赖规则

```
core/     ← 所有模块和插件都可导入
plugins/  ← 所有模块都可导入
db/       ← 所有模块都可导入

modules/auth     → 可导入 core/、db/
modules/system   → 可导入 core/、db/
modules/patient  → 可导入 core/、db/
modules/rag      → 可导入 core/、db/、plugins/
modules/agent    → 可导入 core/、db/、plugins/、modules/rag
modules/audit    → 可导入 core/、db/

❌ 禁止：模块间循环依赖（agent → rag 单向可以，rag → agent 不行）
❌ 禁止：plugins/ 导入 modules/（插件不依赖业务）
❌ 禁止：core/ 导入 modules/ 或 plugins/
```

---

## 7. 路由注册映射

```python
# main.py 中的路由注册
from app.modules.auth.router import router as auth_router
from app.modules.system.router import router as system_router
from app.modules.patient.router import router as patient_router
from app.modules.rag.router import router as rag_router
from app.modules.agent.router import router as agent_router
from app.modules.audit.router import router as audit_router

# 路由前缀保持不变，确保前端零改动
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(system_router, prefix="/api/v1", tags=["system"])
app.include_router(patient_router, prefix="/api/v1", tags=["patient"])
app.include_router(rag_router, prefix="/api/v1", tags=["rag"])
app.include_router(agent_router, prefix="/api/v1", tags=["agent"])
app.include_router(audit_router, prefix="/api/v1", tags=["audit"])
```

> **关键约束**：所有 API 路径与前端保持完全一致，前端不需要任何改动。

---

## 8. 现有文件迁移映射

### 8.1 端点迁移

| 现有文件 | 迁移目标 |
|---------|---------|
| `api/endpoints/auth.py` | `modules/auth/router.py` |
| `api/endpoints/organizations.py` | `modules/system/router.py` |
| `api/endpoints/users.py` | `modules/system/router.py` |
| `api/endpoints/rbac.py` | `modules/system/router.py` |
| `api/endpoints/tenants.py` | `modules/system/router.py` |
| `api/endpoints/menus.py` | `modules/system/router.py` |
| `api/endpoints/api_keys.py` | `modules/system/router.py` |
| `api/endpoints/settings.py` | `modules/system/router.py` |
| `api/endpoints/patients.py` | `modules/patient/router.py` |
| `api/endpoints/health_metrics.py` | `modules/patient/router.py` |
| `api/endpoints/family.py` | `modules/patient/router.py` |
| `api/endpoints/managers.py` | `modules/patient/router.py` |
| `api/endpoints/chat.py` | `modules/rag/router.py` |
| `api/endpoints/documents.py` | `modules/rag/router.py` |
| `api/endpoints/knowledge_bases.py` | `modules/rag/router.py` |
| `api/endpoints/conversations.py` | `modules/rag/router.py` |
| `api/endpoints/audit_logs.py` | `modules/audit/router.py` |
| `api/endpoints/usage.py` | `modules/audit/router.py` |
| `api/endpoints/dashboard.py` | `modules/audit/router.py` |
| `api/endpoints/external_api.py` | `modules/audit/router.py` |

### 8.2 服务迁移

| 现有文件 | 迁移目标 |
|---------|---------|
| `services/chat.py` | 拆分 → `modules/rag/retrieval.py` + `modules/rag/citation.py` |
| `services/rag_ingestion.py` | 拆分 → `modules/rag/ingestion.py` + `plugins/chunker/` |
| `services/query_rewrite.py` | → `modules/rag/query_rewrite.py` |
| `services/rag_evaluation.py` | → `modules/rag/evaluation.py` |
| `services/conversation_context.py` | → `modules/rag/context.py` |
| `services/conversation_compress.py` | → `modules/rag/context.py`（合并） |
| `services/llm.py` | → `plugins/llm/openai_compatible.py` |
| `services/embeddings.py` | → `plugins/embedding/openai_compatible.py` |
| `services/reranker.py` | 拆分 → `plugins/reranker/` 下多个文件 |
| `services/document_parser.py` | → `plugins/parser/pdf_parser.py` |
| `services/provider_registry.py` | → `plugins/registry.py` |
| `services/rbac.py` | → `modules/system/service.py` |
| `services/quota.py` | → `modules/system/quota.py` |
| `services/settings.py` | → `modules/system/service.py`（合并） |
| `services/audit.py` | → `modules/audit/service.py` + `modules/audit/tasks.py` |
| `services/health_alert.py` | → `modules/patient/alert.py` |
| `services/email.py` | → `modules/auth/service.py`（合并） |
| `services/storage.py` | → `core/storage.py`（MinIO 是基础设施） |
| `services/embedding_validation.py` | → `plugins/embedding/base.py`（合并） |
| `services/agent/` | → `modules/agent/`（整体搬迁） |

### 8.3 模型迁移

| 现有模型文件 | 迁移目标 |
|-------------|---------|
| `db/models/user.py` | `modules/auth/models.py` |
| `db/models/organization.py` | `modules/system/models.py` |
| `db/models/rbac.py` | `modules/system/models.py` |
| `db/models/tenant.py` | `modules/system/models.py` |
| `db/models/menu.py` | `modules/system/models.py` |
| `db/models/api_key.py` | `modules/system/models.py` |
| `db/models/settings.py` | `modules/system/models.py` |
| `db/models/patient.py` | `modules/patient/models.py` |
| `db/models/health_metric.py` | `modules/patient/models.py` |
| `db/models/manager.py` | `modules/patient/models.py` |
| `db/models/knowledge.py` | `modules/rag/models.py` |
| `db/models/chat.py` | `modules/rag/models.py` |
| `db/models/audit.py` | `modules/audit/models.py` |
| `db/models/base.py` | `db/base.py`（保持共享） |
| `db/models/__init__.py` | 重写：从各模块 models.py 统一导出 |

---

## 9. 新增配置项

```python
# core/config.py 新增字段
class Settings(BaseSettings):
    # ... 现有配置不变 ...

    # ⭐ OpenTelemetry
    OTLP_ENDPOINT: str = ""              # OTLP 导出地址（如 http://localhost:4317）
    OTEL_SERVICE_NAME: str = "cdm-backend"

    # ⭐ arq Worker
    ARQ_MAX_JOBS: int = 10               # Worker 最大并发任务数
    ARQ_JOB_TIMEOUT: int = 600           # 单任务超时（秒）
```

---

## 10. 迁移策略

采用**模块化渐进迁移**，不一次性推倒：

| 阶段 | 内容 | 风险 |
|------|------|------|
| **阶段 1** | 搭建骨架：创建 `modules/`、`plugins/`、`tasks/`、`telemetry/` 目录 + 基础设施代码 | 低 |
| **阶段 2** | 迁移插件层：将 `llm.py`、`embeddings.py`、`reranker.py` 迁移到 `plugins/` | 低 |
| **阶段 3** | 迁移 `rag` 模块：最复杂模块优先，包含异步任务改造 | 中 |
| **阶段 4** | 迁移 `system`、`auth`、`patient`、`audit` 模块 | 低 |
| **阶段 5** | 迁移 `agent` 模块 | 低 |
| **阶段 6** | 清理旧目录、更新 `__init__.py` 导出、运行全量测试 | 中 |
| **阶段 7** | 接入 OpenTelemetry 链路追踪 | 低 |

**每个阶段完成后运行全量测试（191 tests），确保零回归。**

---

## 11. 不在本次范围内

以下事项明确排除，留待后续迭代：

- 前端任何改动（API 路径完全不变）
- 数据库 Schema 变更（模型只是搬家，字段不变）
- 新增业务功能
- Prometheus 指标暴露与 Grafana 仪表盘（可观测性标准级不含此项）
- 多 Provider 智能路由与 A/B 测试（自治优化架构师的领域，本次不涉及）
