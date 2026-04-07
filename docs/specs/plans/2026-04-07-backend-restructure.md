# 后端系统性重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将后端从扁平三层结构重构为「业务模块垂直切分 + AI 插件体系」架构，引入 arq 异步任务和 OpenTelemetry 链路追踪。

**Architecture:** 6 个业务模块（auth/system/patient/rag/agent/audit）+ 5 个 AI 插件族（llm/embedding/reranker/parser/chunker）+ arq Worker + OpenTelemetry。所有 API 路径保持不变，前端零改动。

**Tech Stack:** FastAPI, SQLAlchemy 2.x Async, arq, OpenTelemetry, structlog

**Spec:** `docs/specs/2026-04-07-backend-restructure-design.md`

---

## 阶段 1：搭建目录骨架与基础设施

### Task 1.1: 创建目录结构

**Files:**
- Create: `backend/app/modules/__init__.py`
- Create: `backend/app/modules/auth/__init__.py`
- Create: `backend/app/modules/system/__init__.py`
- Create: `backend/app/modules/patient/__init__.py`
- Create: `backend/app/modules/rag/__init__.py`
- Create: `backend/app/modules/agent/__init__.py`
- Create: `backend/app/modules/audit/__init__.py`
- Create: `backend/app/plugins/__init__.py`
- Create: `backend/app/plugins/llm/__init__.py`
- Create: `backend/app/plugins/embedding/__init__.py`
- Create: `backend/app/plugins/reranker/__init__.py`
- Create: `backend/app/plugins/parser/__init__.py`
- Create: `backend/app/plugins/chunker/__init__.py`
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/telemetry/__init__.py`

- [ ] **Step 1: 创建所有目录和 `__init__.py`**

```powershell
cd d:\codes\chronic-disease-management\backend\app
$dirs = @(
  "modules", "modules/auth", "modules/system", "modules/patient",
  "modules/rag", "modules/agent", "modules/audit",
  "plugins", "plugins/llm", "plugins/embedding", "plugins/reranker",
  "plugins/parser", "plugins/chunker",
  "tasks", "telemetry"
)
foreach ($d in $dirs) {
  New-Item -ItemType Directory -Path $d -Force
  if (-not (Test-Path "$d/__init__.py")) { "" | Out-File -Encoding utf8 "$d/__init__.py" }
}
```

- [ ] **Step 2: 验证目录结构**

Run: `python -c "import app.modules; import app.plugins; import app.tasks; import app.telemetry; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```
git add -A ; git commit -m "chore: scaffold modules/plugins/tasks/telemetry directory structure"
```

### Task 1.2: 创建统一异常定义

**Files:**
- Create: `backend/app/core/exceptions.py`

- [ ] **Step 1: 创建 exceptions.py**

```python
"""统一业务异常定义"""
from fastapi import HTTPException


class NotFoundError(HTTPException):
    def __init__(self, resource: str = "Resource", detail: str | None = None):
        super().__init__(status_code=404, detail=detail or f"{resource} not found")


class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=403, detail=detail)


class ConflictError(HTTPException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=409, detail=detail)


class QuotaExceededError(HTTPException):
    def __init__(self, detail: str = "Quota exceeded"):
        super().__init__(status_code=429, detail=detail)
```

- [ ] **Step 2: 验证导入**

Run: `python -c "from app.core.exceptions import NotFoundError, ForbiddenError; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```
git add app/core/exceptions.py ; git commit -m "feat: add unified exception definitions"
```

### Task 1.3: 创建插件注册中心

**Files:**
- Create: `backend/app/plugins/registry.py`
- Test: `backend/tests/test_plugin_registry.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_plugin_registry.py
from app.plugins.registry import PluginRegistry


def test_register_and_get():
    PluginRegistry.reset()
    PluginRegistry.register("test_cat", "impl_a", lambda: {"name": "a"})
    result = PluginRegistry.get("test_cat", "impl_a")
    assert result == {"name": "a"}
    PluginRegistry.reset()


def test_lazy_initialization():
    """工厂函数只在首次 get 时调用"""
    PluginRegistry.reset()
    call_count = {"n": 0}

    def factory():
        call_count["n"] += 1
        return "instance"

    PluginRegistry.register("lazy", "impl", factory)
    assert call_count["n"] == 0
    PluginRegistry.get("lazy", "impl")
    assert call_count["n"] == 1
    PluginRegistry.get("lazy", "impl")  # 第二次不再调用
    assert call_count["n"] == 1
    PluginRegistry.reset()


def test_get_unknown_raises():
    PluginRegistry.reset()
    import pytest
    with pytest.raises(KeyError):
        PluginRegistry.get("nonexistent", "x")
    PluginRegistry.reset()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_plugin_registry.py -v`
Expected: FAIL（`ModuleNotFoundError` 或 `ImportError`）

- [ ] **Step 3: 实现 PluginRegistry**

```python
# app/plugins/registry.py
"""统一插件注册中心 — 配置驱动，延迟初始化"""
from typing import Any, Callable


class PluginRegistry:
    _factories: dict[str, dict[str, Callable]] = {}
    _instances: dict[str, dict[str, Any]] = {}

    @classmethod
    def register(cls, category: str, name: str, factory: Callable) -> None:
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
    def list_plugins(cls, category: str) -> list[str]:
        return list(cls._factories.get(category, {}).keys())

    @classmethod
    def _resolve_default(cls, category: str) -> str:
        from app.core.config import settings
        defaults = {
            "llm": "openai_compatible",
            "embedding": "openai_compatible",
            "reranker": settings.RERANKER_PROVIDER.lower().strip() or "noop",
            "parser": "pdf",
            "chunker": "medical_heading",
        }
        return defaults.get(category, "default")

    @classmethod
    def reset(cls) -> None:
        cls._instances.clear()
        cls._factories.clear()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_plugin_registry.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```
git add app/plugins/registry.py tests/test_plugin_registry.py
git commit -m "feat: implement PluginRegistry with lazy init and config-driven defaults"
```

### Task 1.4: 创建 Telemetry 基础设施

**Files:**
- Create: `backend/app/telemetry/tracing.py`
- Create: `backend/app/telemetry/setup.py`
- Create: `backend/app/telemetry/logging.py`
- Modify: `backend/app/core/config.py` — 新增 OTLP 配置
- Test: `backend/tests/test_telemetry.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_telemetry.py
from app.telemetry.tracing import trace_span, traced


def test_trace_span_context_manager():
    """trace_span 上下文管理器不抛异常"""
    with trace_span("test.span", attributes={"key": "value"}):
        result = 1 + 1
    assert result == 2


import asyncio

def test_traced_decorator():
    """traced 装饰器正常包装异步函数"""
    @traced("test.func")
    async def my_func(x: int) -> int:
        return x * 2

    result = asyncio.get_event_loop().run_until_complete(my_func(5))
    assert result == 10
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_telemetry.py -v`
Expected: FAIL

- [ ] **Step 3: 在 config.py 新增配置**

在 `Settings` 类的 CORS 配置之前添加：

```python
    # OpenTelemetry
    OTLP_ENDPOINT: str = ""
    OTEL_SERVICE_NAME: str = "cdm-backend"

    # arq Worker
    ARQ_MAX_JOBS: int = 10
    ARQ_JOB_TIMEOUT: int = 600
```

- [ ] **Step 4: 实现 tracing.py**

```python
# app/telemetry/tracing.py
"""OpenTelemetry 追踪工具 — 提供 trace_span 上下文管理器和 traced 装饰器"""
from contextlib import contextmanager
from functools import wraps
from typing import Any

_tracer = None


def _get_tracer():
    global _tracer
    if _tracer is None:
        try:
            from opentelemetry import trace
            _tracer = trace.get_tracer("cdm.backend")
        except ImportError:
            _tracer = None
    return _tracer


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None):
    tracer = _get_tracer()
    if tracer is None:
        yield None
        return
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

- [ ] **Step 5: 实现 setup.py**

```python
# app/telemetry/setup.py
"""OpenTelemetry SDK 初始化（在 main.py lifespan 中调用）"""
import logging

logger = logging.getLogger(__name__)


def setup_telemetry(app):
    from app.core.config import settings
    if not settings.OTLP_ENDPOINT:
        logger.info("OTLP_ENDPOINT not set, telemetry disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanExporter
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        provider = TracerProvider()
        exporter = OTLPSpanExporter(endpoint=settings.OTLP_ENDPOINT)
        provider.add_span_processor(BatchSpanExporter(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry initialized: endpoint=%s", settings.OTLP_ENDPOINT)
    except ImportError:
        logger.warning("OpenTelemetry packages not installed, skipping")
```

- [ ] **Step 6: 实现 logging.py**

```python
# app/telemetry/logging.py
"""结构化日志配置"""
import logging
import sys


def setup_logging(level: str = "INFO"):
    fmt = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        stream=sys.stderr,
    )
```

- [ ] **Step 7: 运行测试确认通过**

Run: `uv run pytest tests/test_telemetry.py -v`
Expected: 2 passed

- [ ] **Step 8: Commit**

```
git add app/telemetry/ app/core/config.py tests/test_telemetry.py
git commit -m "feat: add telemetry infrastructure (tracing + structured logging)"
```

---

## 阶段 2：迁移 AI 插件层

### Task 2.1: 迁移 LLM 插件

**Files:**
- Create: `backend/app/plugins/llm/base.py`
- Create: `backend/app/plugins/llm/openai_compatible.py`
- Source: `backend/app/services/llm.py` (不删除，保持兼容)

- [ ] **Step 1: 创建 LLM 插件基类**

```python
# app/plugins/llm/base.py
"""LLM 插件接口定义"""
from typing import Protocol, AsyncGenerator


class LLMPlugin(Protocol):
    model_name: str
    async def stream_text(self, prompt: str) -> AsyncGenerator[str, None]: ...
    async def complete_text(self, prompt: str) -> str: ...
```

- [ ] **Step 2: 迁移 OpenAI 兼容实现到插件**

将 `app/services/llm.py` 中的 `OpenAICompatibleLLMProvider` 类复制到 `app/plugins/llm/openai_compatible.py`，末尾添加插件注册：

```python
# app/plugins/llm/openai_compatible.py
"""OpenAI 兼容 LLM 插件实现"""
import logging
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


class OpenAICompatibleLLMPlugin:
    def __init__(self, client: AsyncOpenAI, model_name: str):
        self.client = client
        self.model_name = model_name

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10),
           stop=stop_after_attempt(3), retry=retry_if_exception_type(Exception), reraise=True)
    async def stream_text(self, prompt: str) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            async for chunk in stream:
                text = None
                if chunk.choices:
                    text = chunk.choices[0].delta.content
                if text:
                    yield text
        except Exception as e:
            logger.error(f"LLM streaming failed: {str(e)}")
            raise

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10),
           stop=stop_after_attempt(3), retry=retry_if_exception_type(Exception), reraise=True)
    async def complete_text(self, prompt: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            if not response.choices:
                return ""
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM completion failed: {str(e)}")
            raise


def _create_llm_plugin() -> OpenAICompatibleLLMPlugin:
    if not settings.LLM_API_KEY:
        raise ValueError("请设置 LLM_API_KEY")
    if not settings.LLM_BASE_URL:
        raise ValueError("请设置 LLM_BASE_URL")
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
    return OpenAICompatibleLLMPlugin(client, model_name=settings.CHAT_MODEL)


PluginRegistry.register("llm", "openai_compatible", _create_llm_plugin)
```

- [ ] **Step 3: 更新 `plugins/llm/__init__.py`**

```python
# app/plugins/llm/__init__.py
from app.plugins.llm.base import LLMPlugin  # noqa: F401
import app.plugins.llm.openai_compatible  # noqa: F401 — 触发注册
```

- [ ] **Step 4: 验证插件注册**

Run: `python -c "from app.plugins.llm import LLMPlugin; from app.plugins.registry import PluginRegistry; print(PluginRegistry.list_plugins('llm'))"`
Expected: `['openai_compatible']`

- [ ] **Step 5: Commit**

```
git add app/plugins/llm/ ; git commit -m "feat: migrate LLM provider to plugin architecture"
```

### Task 2.2: 迁移 Embedding 插件

**Files:**
- Create: `backend/app/plugins/embedding/base.py`
- Create: `backend/app/plugins/embedding/openai_compatible.py`
- Source: `backend/app/services/embeddings.py`

- [ ] **Step 1: 创建基类**

```python
# app/plugins/embedding/base.py
from typing import Protocol


class EmbeddingPlugin(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_query(self, text: str) -> list[float]: ...
    def get_dimension(self) -> int | None: ...
```

- [ ] **Step 2: 迁移实现并注册**

将 `app/services/embeddings.py` 中的 `OpenAIEmbeddingProvider` 复制到 `app/plugins/embedding/openai_compatible.py`，类名改为 `OpenAICompatibleEmbeddingPlugin`，末尾添加：

```python
from app.plugins.registry import PluginRegistry

def _create_embedding_plugin():
    from app.core.config import settings
    api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
    base_url = settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL
    if not api_key:
        raise ValueError("请设置 EMBEDDING_API_KEY（或 LLM_API_KEY 作为回退）")
    if not base_url:
        raise ValueError("请设置 EMBEDDING_BASE_URL（或 LLM_BASE_URL 作为回退）")
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return OpenAICompatibleEmbeddingPlugin(client, model_name=settings.EMBEDDING_MODEL)

PluginRegistry.register("embedding", "openai_compatible", _create_embedding_plugin)
```

- [ ] **Step 3: 更新 `__init__.py`，验证，Commit**

方法同 Task 2.1。

```
git add app/plugins/embedding/ ; git commit -m "feat: migrate Embedding provider to plugin architecture"
```

### Task 2.3: 迁移 Reranker 插件

**Files:**
- Create: `backend/app/plugins/reranker/base.py`
- Create: `backend/app/plugins/reranker/noop.py`
- Create: `backend/app/plugins/reranker/simple.py`
- Create: `backend/app/plugins/reranker/openai_compatible.py`
- Source: `backend/app/services/reranker.py`

- [ ] **Step 1: 创建基类**

```python
# app/plugins/reranker/base.py
from typing import Protocol, Any
from collections.abc import Sequence


class RerankerPlugin(Protocol):
    async def rerank(self, query: str, results: Sequence[Any], limit: int) -> list[Any]: ...
```

- [ ] **Step 2: 将现有 3 个实现拆分为独立文件**

从 `services/reranker.py` 拆出：
- `NoopRerankerProvider` → `plugins/reranker/noop.py`（类名改为 `NoopRerankerPlugin`）
- `SimpleRerankerProvider` → `plugins/reranker/simple.py`
- `OpenAICompatibleRerankerProvider` → `plugins/reranker/openai_compatible.py`

每个文件末尾添加 `PluginRegistry.register("reranker", "<name>", factory)`。

- [ ] **Step 3: 更新 `__init__.py` 触发所有注册，验证，Commit**

```
git add app/plugins/reranker/ ; git commit -m "feat: migrate Reranker providers to plugin architecture"
```

### Task 2.4: 迁移文档解析器插件

**Files:**
- Create: `backend/app/plugins/parser/base.py`
- Create: `backend/app/plugins/parser/pdf_parser.py`
- Create: `backend/app/plugins/parser/text_parser.py`
- Create: `backend/app/plugins/parser/docx_parser.py`
- Source: `backend/app/services/document_parser.py`

- [ ] **Step 1: 创建基类**

```python
# app/plugins/parser/base.py
from typing import Protocol
from dataclasses import dataclass


@dataclass(slots=True)
class ParseResult:
    text: str
    pages: list[str]


class DocumentParseError(Exception):
    pass


class ParserPlugin(Protocol):
    supported_types: list[str]
    def parse(self, file_bytes: bytes, filename: str) -> ParseResult: ...
```

- [ ] **Step 2: 将现有解析函数拆为 3 个插件文件**

从 `services/document_parser.py` 拆出：
- `_parse_pdf_document` → `plugins/parser/pdf_parser.py` 的 `PdfParserPlugin.parse()`
- `_parse_text_document` → `plugins/parser/text_parser.py`
- `_parse_docx_document` → `plugins/parser/docx_parser.py`

工具函数 `_normalize_text` 放入 `base.py`。

各文件末尾注册：`PluginRegistry.register("parser", "pdf", lambda: PdfParserPlugin())`

- [ ] **Step 3: 验证，Commit**

```
git add app/plugins/parser/ ; git commit -m "feat: migrate document parsers to plugin architecture"
```

### Task 2.5: 创建切块策略插件

**Files:**
- Create: `backend/app/plugins/chunker/base.py`
- Create: `backend/app/plugins/chunker/medical_heading.py`
- Source: `backend/app/services/rag_ingestion.py`（切块相关函数）

- [ ] **Step 1: 创建基类**

```python
# app/plugins/chunker/base.py
from typing import Protocol
from dataclasses import dataclass


@dataclass(slots=True)
class ChunkResult:
    content: str
    page_number: int | None
    section_title: str | None
    char_start: int
    char_end: int


class ChunkerPlugin(Protocol):
    name: str
    def chunk(self, text: str, pages: list[str] | None = None,
              chunk_size: int = 800, chunk_overlap: int = 150) -> list[ChunkResult]: ...
```

- [ ] **Step 2: 从 `rag_ingestion.py` 提取切块逻辑到插件**

将 `split_document_text()`、`MEDICAL_HEADING_RE`、`_SENTENCE_BOUNDARY_RE`、`_find_page_number`、`_build_page_boundaries` 等函数迁移到 `plugins/chunker/medical_heading.py`，封装为 `MedicalHeadingChunkerPlugin` 类。

末尾注册：`PluginRegistry.register("chunker", "medical_heading", lambda: MedicalHeadingChunkerPlugin())`

- [ ] **Step 3: 验证，Commit**

```
git add app/plugins/chunker/ ; git commit -m "feat: extract chunking logic to plugin architecture"
```

### Task 2.6: 创建兼容层并运行全量测试

**Files:**
- Modify: `backend/app/services/provider_registry.py` — 改为委托到 PluginRegistry

- [ ] **Step 1: 修改 provider_registry.py 为兼容桥接**

```python
# app/services/provider_registry.py（兼容层 — 委托到 PluginRegistry）
from app.plugins.registry import PluginRegistry
import app.plugins.llm  # noqa: F401 — 触发插件注册
import app.plugins.embedding  # noqa: F401
import app.plugins.reranker  # noqa: F401


class ProviderRegistry:
    """向后兼容层：所有调用委托到 PluginRegistry"""
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_llm(self):
        return PluginRegistry.get("llm")

    def get_embedding(self):
        return PluginRegistry.get("embedding")

    def get_reranker(self):
        return PluginRegistry.get("reranker")


registry = ProviderRegistry.get_instance()
```

- [ ] **Step 2: 运行全量测试**

Run: `uv run pytest tests/ -v --tb=short`
Expected: 191 tests passed（所有现有测试不受影响）

- [ ] **Step 3: Commit**

```
git add app/services/provider_registry.py ; git commit -m "refactor: bridge ProviderRegistry to PluginRegistry for backward compat"
```

---

## 阶段 3：迁移 RAG 模块（含异步任务改造）

> 这是最复杂的模块，包含检索管线、入库管线、对话、知识库全部逻辑。

### Task 3.1: 迁移 RAG 模型

**Files:**
- Create: `backend/app/modules/rag/models.py`
- Source: `backend/app/db/models/knowledge.py`, `backend/app/db/models/chat.py`

- [ ] **Step 1: 创建 `modules/rag/models.py`**

将 `db/models/knowledge.py`（KnowledgeBase、Document、Chunk）和 `db/models/chat.py`（Conversation、Message、UsageLog）的内容合并复制到此文件。保持所有 import 和类定义不变。

- [ ] **Step 2: 更新 `db/models/__init__.py` 的导入源**

将原来的：
```python
from .knowledge import KnowledgeBase, Document, Chunk
from .chat import Conversation, Message, UsageLog
```
改为：
```python
from app.modules.rag.models import KnowledgeBase, Document, Chunk
from app.modules.rag.models import Conversation, Message, UsageLog
```

- [ ] **Step 3: 运行全量测试验证兼容性**

Run: `uv run pytest tests/ -x --tb=short`
Expected: 全部通过

- [ ] **Step 4: Commit**

```
git add app/modules/rag/models.py app/db/models/__init__.py
git commit -m "refactor: migrate RAG models to modules/rag/"
```

### Task 3.2: 迁移 RAG Schemas

**Files:**
- Create: `backend/app/modules/rag/schemas.py`
- Source: `backend/app/schemas/document.py`, `backend/app/schemas/admin.py`（对话相关部分）

- [ ] **Step 1: 将 RAG 相关的 Pydantic 模型复制到 `modules/rag/schemas.py`**

从 `schemas/document.py` 复制 Document 相关 schema；从 `schemas/admin.py` 复制 `ConversationRead` 等。原文件保留为兼容导出。

- [ ] **Step 2: 验证导入，Commit**

```
git add app/modules/rag/schemas.py ; git commit -m "refactor: migrate RAG schemas to modules/rag/"
```

### Task 3.3: 迁移查询改写与上下文服务

**Files:**
- Create: `backend/app/modules/rag/query_rewrite.py` — 从 `services/query_rewrite.py` 复制
- Create: `backend/app/modules/rag/context.py` — 合并 `services/conversation_context.py` + `services/conversation_compress.py`

- [ ] **Step 1: 复制 query_rewrite.py**

原样复制 `services/query_rewrite.py` 到 `modules/rag/query_rewrite.py`。仅修改内部导入（如果有）。

- [ ] **Step 2: 合并 context.py**

将 `services/conversation_context.py` 和 `services/conversation_compress.py` 合并为 `modules/rag/context.py`。

- [ ] **Step 3: 验证导入，Commit**

```
git add app/modules/rag/query_rewrite.py app/modules/rag/context.py
git commit -m "refactor: migrate query_rewrite and context to modules/rag/"
```

### Task 3.4: 创建 RAG 检索管线

**Files:**
- Create: `backend/app/modules/rag/retrieval.py`
- Create: `backend/app/modules/rag/citation.py`
- Source: `backend/app/services/chat.py`

- [ ] **Step 1: 从 `services/chat.py` 拆分检索逻辑到 `retrieval.py`**

提取 `retrieve_chunks`（含 `_vector_search`、`_keyword_search`、`_rrf_fuse` 等）到 `modules/rag/retrieval.py`。所有函数签名保持不变。添加 `trace_span` 包装：

```python
from app.telemetry.tracing import trace_span

async def retrieve_chunks(db, query, kb_id, org_id, ...):
    with trace_span("rag.retrieve", {"kb_id": kb_id}):
        # 现有检索逻辑
        ...
```

- [ ] **Step 2: 拆分引用逻辑到 `citation.py`**

提取 `build_rag_prompt`、`extract_statement_citations_structured` 到 `modules/rag/citation.py`。

- [ ] **Step 3: 在 `services/chat.py` 顶部原地替换为兼容导出**

```python
# 向后兼容导出（阶段6清理时删除）
from app.modules.rag.retrieval import retrieve_chunks  # noqa: F401
from app.modules.rag.citation import build_rag_prompt, extract_statement_citations_structured  # noqa: F401
```

- [ ] **Step 4: 运行全量测试**

Run: `uv run pytest tests/ -x --tb=short`
Expected: 全部通过

- [ ] **Step 5: Commit**

```
git add app/modules/rag/retrieval.py app/modules/rag/citation.py app/services/chat.py
git commit -m "refactor: extract retrieval pipeline and citation to modules/rag/"
```

### Task 3.5: 创建入库管线 + arq 异步任务

**Files:**
- Create: `backend/app/modules/rag/ingestion.py` — 入库管线编排
- Create: `backend/app/modules/rag/tasks.py` — arq 任务定义
- Create: `backend/app/tasks/worker.py` — arq Worker 配置

- [ ] **Step 1: 创建入库管线**

```python
# app/modules/rag/ingestion.py
"""文档入库管线：Parser → Chunker → Embedding → Store"""
import logging
from app.plugins.registry import PluginRegistry
from app.telemetry.tracing import trace_span, traced

logger = logging.getLogger(__name__)


class IngestionPipeline:
    @traced("rag.ingest")
    async def run(self, document_id: int, org_id: int):
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text
        from app.modules.rag.models import Document, Chunk
        from app.core.snowflake import get_next_id
        from app.core.config import settings

        async with AsyncSessionLocal() as db:
            await db.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(org_id)},
            )
            document = await db.get(Document, document_id)
            if not document:
                logger.error("Document %s not found", document_id)
                return

            try:
                # 1. 解析
                with trace_span("rag.parse", {"file_type": document.file_type or "unknown"}):
                    file_type = (document.file_type or "pdf").lower()
                    parser_name = {"pdf": "pdf", "txt": "text", "docx": "docx",
                                   "md": "text", "markdown": "text"}.get(file_type, "pdf")
                    parser = PluginRegistry.get("parser", parser_name)
                    from app.services.storage import get_storage_service
                    # 此处需要从 MinIO 获取文件内容
                    parse_result = parser.parse(document.raw_content, document.file_name)

                # 2. 切块
                with trace_span("rag.chunk"):
                    chunker = PluginRegistry.get("chunker")
                    chunks = chunker.chunk(parse_result.text, parse_result.pages)

                # 3. 向量化
                with trace_span("rag.embed", {"chunk_count": len(chunks)}):
                    embedder = PluginRegistry.get("embedding")
                    contents = [c.content for c in chunks]
                    vectors = await self._batch_embed(embedder, contents)

                # 4. 写入
                with trace_span("rag.store"):
                    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                        db_chunk = Chunk(
                            id=get_next_id(),
                            document_id=document.id,
                            kb_id=document.kb_id,
                            tenant_id=document.tenant_id,
                            org_id=document.org_id,
                            content=chunk.content,
                            embedding=vector,
                            page_number=chunk.page_number,
                            section_title=chunk.section_title,
                            chunk_index=i,
                        )
                        db.add(db_chunk)

                document.status = "completed"
                document.chunk_count = len(chunks)
                await db.commit()
                logger.info("Document %s ingested: %d chunks", document_id, len(chunks))

            except Exception:
                document.status = "failed"
                await db.commit()
                logger.exception("Document %s ingestion failed", document_id)
                raise

    async def _batch_embed(self, embedder, texts: list[str]) -> list[list[float]]:
        from app.core.config import settings
        batch_size = settings.EMBEDDING_BATCH_SIZE
        all_vectors = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            vectors = await embedder.embed_documents(batch)
            all_vectors.extend(vectors)
        return all_vectors
```

- [ ] **Step 2: 创建 arq 任务**

```python
# app/modules/rag/tasks.py
"""RAG 模块异步任务"""
import logging

logger = logging.getLogger(__name__)


async def process_document_task(ctx, document_id: int, org_id: int):
    """arq 异步任务：文档入库"""
    logger.info("Starting document ingestion: doc=%s org=%s", document_id, org_id)
    from app.modules.rag.ingestion import IngestionPipeline
    pipeline = IngestionPipeline()
    await pipeline.run(document_id, org_id)
```

- [ ] **Step 3: 创建 arq Worker 配置**

```python
# app/tasks/worker.py
"""arq Worker 启动配置"""
from arq.connections import RedisSettings
from app.core.config import settings


async def startup(ctx):
    import logging
    logging.basicConfig(level=logging.INFO)
    # 触发插件注册
    import app.plugins.llm  # noqa: F401
    import app.plugins.embedding  # noqa: F401
    import app.plugins.reranker  # noqa: F401
    import app.plugins.parser  # noqa: F401
    import app.plugins.chunker  # noqa: F401


async def shutdown(ctx):
    pass


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = settings.ARQ_MAX_JOBS
    job_timeout = settings.ARQ_JOB_TIMEOUT
    functions = []

    @classmethod
    def collect_functions(cls):
        from app.modules.rag.tasks import process_document_task
        cls.functions = [process_document_task]
        return cls.functions


# 收集任务
WorkerSettings.collect_functions()
```

- [ ] **Step 4: 验证 Worker 配置可导入**

Run: `python -c "from app.tasks.worker import WorkerSettings; print(len(WorkerSettings.functions), 'tasks')"`
Expected: `1 tasks`

- [ ] **Step 5: Commit**

```
git add app/modules/rag/ingestion.py app/modules/rag/tasks.py app/tasks/worker.py
git commit -m "feat: create async ingestion pipeline with arq worker"
```

### Task 3.6: 创建 RAG 路由

**Files:**
- Create: `backend/app/modules/rag/router.py`
- Create: `backend/app/modules/rag/service.py`

- [ ] **Step 1: 从现有端点合并路由**

将以下端点文件的路由函数复制到 `modules/rag/router.py`：
- `api/endpoints/chat.py` → `/chat` 路由
- `api/endpoints/knowledge_bases.py` → `/kb` 路由
- `api/endpoints/documents.py` → `/documents` 路由
- `api/endpoints/conversations.py` → `/conversations` 路由

修改导入路径指向 `modules/rag/` 下的模型和服务。

- [ ] **Step 2: 创建 service.py 封装业务逻辑**

将端点中的复杂业务逻辑提取到 `modules/rag/service.py`，路由层保持薄层。

- [ ] **Step 3: 验证，暂不切换路由注册（保持旧路由工作）**

- [ ] **Step 4: Commit**

```
git add app/modules/rag/router.py app/modules/rag/service.py
git commit -m "refactor: create RAG module router consolidating chat/kb/docs/conversations"
```

### Task 3.7: 迁移 RAG 评估

**Files:**
- Create: `backend/app/modules/rag/evaluation.py` — 从 `services/rag_evaluation.py` 复制

- [ ] **Step 1: 复制并调整导入路径**
- [ ] **Step 2: Commit**

```
git add app/modules/rag/evaluation.py ; git commit -m "refactor: migrate RAG evaluation to modules/rag/"
```

---

## 阶段 4：迁移 system/auth/patient/audit 模块

### Task 4.1: 迁移 auth 模块

**Files:**
- Create: `backend/app/modules/auth/models.py` — User, PasswordResetToken
- Create: `backend/app/modules/auth/router.py` — 从 `api/endpoints/auth.py`
- Create: `backend/app/modules/auth/service.py` — 登录/注册/密码重置逻辑
- Create: `backend/app/modules/auth/schemas.py` — 从 `schemas/user.py`

- [ ] **Step 1: 迁移模型** — 复制 `db/models/user.py` → `modules/auth/models.py`
- [ ] **Step 2: 更新 `db/models/__init__.py`** — 改从 `modules/auth/models` 导入
- [ ] **Step 3: 迁移路由和 schema**
- [ ] **Step 4: 合并 `services/email.py` 逻辑到 `modules/auth/service.py`**
- [ ] **Step 5: 运行全量测试**
- [ ] **Step 6: Commit**

```
git add app/modules/auth/ app/db/models/__init__.py
git commit -m "refactor: migrate auth module (User, JWT, password reset)"
```

### Task 4.2: 迁移 system 模块

**Files:**
- Create: `backend/app/modules/system/models.py` — Tenant, Organization, Role, Menu, ApiKey, SystemSetting...
- Create: `backend/app/modules/system/router.py` — 合并 organizations/users/rbac/tenants/menus/api_keys/settings
- Create: `backend/app/modules/system/service.py` — 合并 rbac + settings 服务
- Create: `backend/app/modules/system/quota.py` — 从 `services/quota.py`
- Create: `backend/app/modules/system/schemas.py`

- [ ] **Step 1-4: 按模型→schema→服务→路由顺序迁移**

迁移源：
- 模型：`db/models/tenant.py` + `organization.py` + `rbac.py` + `menu.py` + `api_key.py` + `settings.py`
- 路由：`api/endpoints/organizations.py` + `users.py` + `rbac.py` + `tenants.py` + `menus.py` + `api_keys.py` + `settings.py`
- 服务：`services/rbac.py` + `services/quota.py` + `services/settings.py`
- Schema：`schemas/organization.py` + `rbac.py` + `menu.py` + `api_key.py`

- [ ] **Step 5: 更新 `db/models/__init__.py`** — 改从 `modules/system/models` 导入
- [ ] **Step 6: 运行全量测试**
- [ ] **Step 7: Commit**

```
git add app/modules/system/ app/db/models/__init__.py
git commit -m "refactor: migrate system module (org, rbac, menu, quota, settings)"
```

### Task 4.3: 迁移 patient 模块

**Files:**
- Create: `backend/app/modules/patient/models.py` — PatientProfile, HealthMetric, ManagerProfile...
- Create: `backend/app/modules/patient/router.py` — 合并 patients/health_metrics/family/managers
- Create: `backend/app/modules/patient/service.py`
- Create: `backend/app/modules/patient/alert.py` — 从 `services/health_alert.py`
- Create: `backend/app/modules/patient/schemas.py`

- [ ] **Step 1-4: 模型→schema→服务→路由→告警**
- [ ] **Step 5: 更新 `db/models/__init__.py`**
- [ ] **Step 6: 运行全量测试**
- [ ] **Step 7: Commit**

```
git add app/modules/patient/ app/db/models/__init__.py
git commit -m "refactor: migrate patient module (profiles, metrics, family, managers)"
```

### Task 4.4: 迁移 audit 模块

**Files:**
- Create: `backend/app/modules/audit/models.py` — AuditLog
- Create: `backend/app/modules/audit/router.py` — 合并 audit_logs/usage/dashboard/external_api
- Create: `backend/app/modules/audit/service.py` — 从 `services/audit.py`
- Create: `backend/app/modules/audit/tasks.py` — 审计异步任务（替代 fire_audit 的 create_task）

- [ ] **Step 1: 迁移模型和服务**
- [ ] **Step 2: 创建审计异步任务**

```python
# app/modules/audit/tasks.py
async def write_audit_log_task(ctx, tenant_id: int, user_id: int, org_id: int | None,
                                action: str, resource_type: str,
                                resource_id: int | None, details: str | None):
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import text
    from app.modules.audit.models import AuditLog
    async with AsyncSessionLocal() as db:
        if tenant_id:
            await db.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
            )
        log = AuditLog(
            tenant_id=tenant_id, user_id=user_id, org_id=org_id,
            action=action, resource_type=resource_type,
            resource_id=resource_id, details=details,
        )
        db.add(log)
        await db.commit()
```

- [ ] **Step 3: 更新 Worker 注册审计任务**

在 `tasks/worker.py` 的 `collect_functions` 中添加 `write_audit_log_task`。

- [ ] **Step 4: 运行全量测试**
- [ ] **Step 5: Commit**

```
git add app/modules/audit/ app/tasks/worker.py app/db/models/__init__.py
git commit -m "refactor: migrate audit module with arq async tasks"
```

---

## 阶段 5：迁移 Agent 模块

### Task 5.1: 搬迁 Agent 目录

**Files:**
- Create: `backend/app/modules/agent/` — 整体搬迁 `services/agent/`

- [ ] **Step 1: 复制 `services/agent/` 全部内容到 `modules/agent/`**

文件映射（保持内部结构不变）：
- `services/agent/__init__.py` → `modules/agent/__init__.py`
- `services/agent/graph.py` → `modules/agent/graph.py`
- `services/agent/state.py` → `modules/agent/state.py`
- `services/agent/memory.py` → `modules/agent/memory.py`
- `services/agent/security.py` → `modules/agent/security.py`
- `services/agent/skills/` → `modules/agent/skills/`（整目录）

- [ ] **Step 2: 修改内部导入路径**

将所有 `from app.services.agent.xxx` 改为 `from app.modules.agent.xxx`。
将 `from app.services.chat` 改为 `from app.modules.rag.retrieval`。

- [ ] **Step 3: 在 `services/agent/__init__.py` 创建兼容导出**

```python
# 向后兼容（阶段6清理）
from app.modules.agent import SecurityContext, skill_registry, run_agent  # noqa: F401
```

- [ ] **Step 4: 创建 Agent 路由**

```python
# app/modules/agent/router.py
from fastapi import APIRouter
router = APIRouter()
# Agent 模式入口复用自 rag router 的 use_agent=true 逻辑
```

- [ ] **Step 5: 运行全量测试**

Run: `uv run pytest tests/ -x --tb=short`
Expected: 全部通过

- [ ] **Step 6: Commit**

```
git add app/modules/agent/ app/services/agent/__init__.py
git commit -m "refactor: migrate agent module to modules/agent/"
```

---

## 阶段 6：清理旧目录 + 切换路由注册

### Task 6.1: 切换 main.py 路由注册

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/app/api/api.py` (重写)

- [ ] **Step 1: 重写 api.py 为模块路由注册**

```python
# app/api/api.py
from fastapi import APIRouter
from app.modules.auth.router import router as auth_router
from app.modules.system.router import router as system_router
from app.modules.patient.router import router as patient_router
from app.modules.rag.router import router as rag_router
from app.modules.audit.router import router as audit_router

api_router = APIRouter()

# 路由前缀保持与原来完全一致
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# system 模块内含多个子路由，前缀在模块内的 router 中定义
api_router.include_router(system_router)

# patient 模块
api_router.include_router(patient_router)

# rag 模块
api_router.include_router(rag_router)

# audit 模块
api_router.include_router(audit_router)
```

- [ ] **Step 2: 在 main.py 添加 telemetry 初始化**

在 `app = FastAPI(...)` 之后、中间件之前添加：

```python
from app.telemetry.setup import setup_telemetry
setup_telemetry(app)
```

- [ ] **Step 3: 运行全量测试**

Run: `uv run pytest tests/ -x --tb=short`
Expected: 全部通过

- [ ] **Step 4: Commit**

```
git add app/api/api.py app/main.py
git commit -m "refactor: switch to module-based route registration"
```

### Task 6.2: 迁移 storage.py 到 core/

**Files:**
- Move: `backend/app/services/storage.py` → `backend/app/core/storage.py`

- [ ] **Step 1: 复制到 core/storage.py**
- [ ] **Step 2: 更新所有 `from app.services.storage` 导入**
- [ ] **Step 3: 在 `services/storage.py` 创建兼容导出**

```python
from app.core.storage import StorageService, get_storage_service  # noqa: F401
```

- [ ] **Step 4: Commit**

```
git add app/core/storage.py app/services/storage.py
git commit -m "refactor: move storage service to core/ (infrastructure)"
```

### Task 6.3: 更新测试导入路径

**Files:**
- Modify: `backend/tests/` 下所有受影响的测试文件

- [ ] **Step 1: 全局搜索替换测试中的旧导入路径**

需要替换的模式：
- `from app.services.chat import` → `from app.modules.rag.retrieval import` 或 `from app.modules.rag.citation import`
- `from app.services.agent` → `from app.modules.agent`
- `from app.services.audit import` → `from app.modules.audit.service import`
- `from app.services.query_rewrite import` → `from app.modules.rag.query_rewrite import`
- `from app.services.rag_ingestion import` → 需按具体函数判断来源
- `from app.services.rag_evaluation import` → `from app.modules.rag.evaluation import`

由于旧文件保留了兼容导出，这一步**可以渐进执行**，不急于一次替换全部。

- [ ] **Step 2: 运行全量测试**

Run: `uv run pytest tests/ -v --tb=short`
Expected: 191 tests passed

- [ ] **Step 3: Commit**

```
git add tests/ ; git commit -m "refactor: update test imports to new module paths"
```

### Task 6.4: 清理旧目录中的源文件

**Files:**
- Delete: `backend/app/api/endpoints/` 下的 20 个旧端点文件（保留目录和 `__init__.py`）
- Delete: `backend/app/services/` 下的 19 个旧服务文件（保留 `agent/` 兼容导出和 `__init__.py`）
- Delete: `backend/app/db/models/` 下已迁移的模型文件（保留 `base.py` 和 `__init__.py`）

- [ ] **Step 1: 删除旧端点文件**

```powershell
$oldEndpoints = @("auth","chat","conversations","documents","knowledge_bases",
  "patients","health_metrics","family","managers",
  "organizations","users","rbac","tenants","menus","api_keys","settings",
  "audit_logs","usage","dashboard","external_api")
foreach ($f in $oldEndpoints) {
  Remove-Item "app/api/endpoints/$f.py" -ErrorAction SilentlyContinue
}
```

- [ ] **Step 2: 删除旧服务文件**

所有已迁移到 `modules/` 或 `plugins/` 的服务文件。保留 `services/__init__.py` 和 `services/agent/__init__.py`（兼容导出）。

- [ ] **Step 3: 删除旧模型文件**

已迁移到各模块的 `models.py` 中的文件（保留 `base.py`、`__init__.py`）。

- [ ] **Step 4: 运行全量测试**

Run: `uv run pytest tests/ -v --tb=short`
Expected: 191 tests passed

- [ ] **Step 5: Commit**

```
git add -A ; git commit -m "chore: remove legacy endpoint/service/model files after migration"
```

---

## 阶段 7：接入 OpenTelemetry 链路追踪

### Task 7.1: 添加 OpenTelemetry 依赖

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: 在 dependencies 中添加 OTel 包**

```toml
    "opentelemetry-api>=1.25.0",
    "opentelemetry-sdk>=1.25.0",
    "opentelemetry-exporter-otlp-proto-grpc>=1.25.0",
    "opentelemetry-instrumentation-fastapi>=0.46b0",
    "opentelemetry-instrumentation-sqlalchemy>=0.46b0",
    "opentelemetry-instrumentation-redis>=0.46b0",
    "structlog>=24.1.0",
```

- [ ] **Step 2: 安装依赖**

Run: `uv sync`

- [ ] **Step 3: Commit**

```
git add pyproject.toml uv.lock ; git commit -m "deps: add OpenTelemetry and structlog"
```

### Task 7.2: 为 RAG 管线各节点添加 trace span

**Files:**
- Modify: `backend/app/modules/rag/retrieval.py`
- Modify: `backend/app/modules/rag/ingestion.py`
- Modify: `backend/app/modules/rag/router.py`（chat 端点）

- [ ] **Step 1: 在 retrieval.py 的每个阶段添加 trace_span**

确认以下位置已添加 span（Task 3.4 中应已完成）：
- `rag.query_rewrite`
- `rag.multi_query`
- `rag.hybrid_search`
- `rag.rrf_fusion`
- `rag.rerank`

- [ ] **Step 2: 在 chat 端点添加顶级 span**

```python
from app.telemetry.tracing import trace_span

@router.post("")
async def chat_endpoint(request: ChatRequest, ...):
    with trace_span("rag.chat_request", {"kb_id": request.kb_id, "user_id": current_user.id}):
        # 现有逻辑
        ...
```

- [ ] **Step 3: 在 ingestion pipeline 确认 span 完整**

确认 Task 3.5 中的 `rag.parse`、`rag.chunk`、`rag.embed`、`rag.store` span 已到位。

- [ ] **Step 4: 运行全量测试**

Run: `uv run pytest tests/ -v --tb=short`
Expected: 全部通过

- [ ] **Step 5: Commit**

```
git add app/modules/rag/ ; git commit -m "feat: add OpenTelemetry trace spans to RAG pipeline"
```

### Task 7.3: 更新 .env.example

**Files:**
- Modify: `backend/.env.example`

- [ ] **Step 1: 添加新配置项文档**

```env
# --- OpenTelemetry ---
# OTLP_ENDPOINT=http://localhost:4317    # OTLP gRPC 导出地址（Jaeger/Tempo/SigNoz）
# OTEL_SERVICE_NAME=cdm-backend

# --- arq Worker ---
# ARQ_MAX_JOBS=10                        # Worker 最大并发任务数
# ARQ_JOB_TIMEOUT=600                    # 单任务超时（秒）
```

- [ ] **Step 2: Commit**

```
git add .env.example ; git commit -m "docs: add OTLP and arq config to .env.example"
```

---

## 交付检查清单

- [ ] 全量测试通过（191 tests）
- [ ] 所有 API 路径与重构前完全一致（前端零改动）
- [ ] `arq Worker` 可通过 `uv run arq app.tasks.worker.WorkerSettings` 启动
- [ ] `PluginRegistry` 正确注册 5 个插件族
- [ ] `telemetry/tracing.py` 的 `trace_span` 在 OTLP 未配置时不报错
- [ ] 更新 `GEMINI.md` 中的目录结构文档
- [ ] 旧 `api/endpoints/`、`services/`、`db/models/` 中已迁移的文件已删除

