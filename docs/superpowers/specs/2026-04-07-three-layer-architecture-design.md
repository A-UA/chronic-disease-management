# 三层架构重构：Routers → Services → AI 领域层

**状态**: 设计完成，待实施
**日期**: 2026-04-07
**替代**: `2026-04-07-architectural-extraction-design.md`（已否决）

## 1. 背景与动机

### 1.1 当前问题

当前 `app/modules/` 采用按业务域垂直切分，每个模块混合了 HTTP 路由、业务逻辑、AI 计算三种职责：

- `modules/rag/router_chat.py`（440 行）同时承担路由定义、SSE 流式编排、对话管理、配额扣减
- `modules/rag/chat_service.py` 与 `retrieval.py` 存在约 200 行重复代码（类型定义、函数实现）
- `modules/agent/` 是纯 AI 逻辑却与 HTTP 路由层同级
- `core/` 包含基础设施（config/security）但命名未体现
- `db/` 仅 2 个非 model 文件，层级冗余
- `api/` 仅 2 个文件，可归并

### 1.2 行业参考

| 项目 | ⭐ Stars | 分层模式 |
|------|---------|---------|
| Open WebUI | 130k | `routers/` + `retrieval/`（AI 独立包） |
| Dify | ~120k | `controllers/` → `services/` → `core/rag/` + `core/agent/` |
| Netflix Dispatch | 6.4k | `views` → `flows` → `service` + 独立 `ai/` 包 |

所有含 AI 功能的成熟项目均将 AI 计算层独立为顶级包。

## 2. 设计目标

1. **职责分离**：严格区分 HTTP 适配（routers）、业务编排（services）、AI 领域逻辑（ai）
2. **依赖单向**：routers → services → ai，禁止反向
3. **命名语义化**：每个顶级包名即代表其职责
4. **零 API 变更**：所有 18 个 URL 端点保持不变，前端零改动
5. **消除技术债**：合并重复代码、拆解臃肿路由

## 3. 架构设计

### 3.1 层级定义

| 层级 | 目录 | 职责 | 允许的依赖 |
|------|------|------|-----------|
| **Routers** | `app/routers/` | HTTP 薄适配器：路由定义、请求校验、响应封装、FastAPI 依赖注入 | → services, ai, models, base |
| **Services** | `app/services/` | 业务编排：DB 事务管理、配额扣减、SSE 流式处理、审计触发 | → ai, models, base |
| **AI** | `app/ai/` | AI 领域层：检索算法、Prompt 构建、引用提取、Agent 状态机 | → models, plugins, base, telemetry |
| **Base** | `app/base/` | 基础设施：配置、安全、数据库连接、对象存储、雪花 ID | → 无（底层） |
| **Models** | `app/models/` | ORM 模型定义 | → base |

### 3.2 依赖方向图

```
routers/ ──→ services/ ──→ ai/
   │              │          │
   │              └─→ models └─→ plugins/
   └─→ routers/deps      │        │
                  └─→ base/ ←─────┘
                          ↑
                   telemetry/ (可被任意层引用)
```

> **规则**：
> - 禁止反向依赖（ai 不得 import routers 或 services）
> - `ai/` 可接受通过参数传入的 `AsyncSession`，但不得自建 session（`AsyncSessionLocal()` 要在 services 层调用）
> - `models/` 和 `telemetry/` 是底层包，可被任意层引用

### 3.3 已知设计妥协

1. **`ai/` 并非"纯计算"**：`retrieval.py`、`ingestion.py`、`context.py` 需要 DB 查询（接收外部传入的 `AsyncSession`）。定义为"AI 领域层"而非"纯计算层"，后续可进一步拆离 DB 依赖。
2. **`services/auth/` 等单文件域**：为保持结构一致性，接受每个域仅 1 个文件 + 1 个 `__init__.py` 的代价。
3. **`ingestion.py` 自建 session**：当前通过 `AsyncSessionLocal()` 自建 session（因为是 arq worker 调用），迁移时暂保留，后续优化时应改为由 worker 传入 session。

## 4. 目录结构

```
app/
├── main.py
├── seed.py                              ← db/seed_data.py
│
├── models/                              ← db/models/（提升为顶级包）
│   ├── __init__.py
│   ├── base.py
│   ├── user.py
│   ├── tenant.py
│   ├── organization.py
│   ├── rbac.py
│   ├── menu.py
│   ├── patient.py
│   ├── health_metric.py
│   ├── manager.py
│   ├── knowledge.py
│   ├── chat.py
│   ├── audit.py
│   ├── settings.py
│   └── api_key.py
│
├── schemas/                             （不变）
│
├── routers/                             ← modules/ 中的 router 文件
│   ├── __init__.py                      ← api/api.py（路由聚合）
│   ├── deps.py                          ← api/deps.py（依赖注入）
│   ├── auth/
│   │   ├── __init__.py                  re-export router
│   │   └── router.py                   ← modules/auth/router.py
│   ├── audit/
│   │   ├── __init__.py                  re-export router
│   │   └── router.py                   ← modules/audit/router.py
│   ├── patient/
│   │   ├── __init__.py
│   │   ├── patients.py                 ← router_patients.py（去前缀）
│   │   ├── health_metrics.py
│   │   ├── family.py
│   │   └── managers.py
│   ├── system/
│   │   ├── __init__.py
│   │   ├── api_keys.py
│   │   ├── dashboard.py
│   │   ├── external_api.py
│   │   ├── menus.py
│   │   ├── organizations.py
│   │   ├── rbac.py
│   │   ├── settings.py
│   │   ├── tenants.py
│   │   ├── usage.py
│   │   └── users.py
│   └── rag/
│       ├── __init__.py
│       ├── chat.py                      ← router_chat.py（瘦身）
│       ├── conversations.py
│       ├── documents.py
│       └── knowledge_bases.py
│
├── services/                            新建
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── email.py                    ← modules/auth/email.py
│   ├── audit/
│   │   ├── __init__.py
│   │   └── service.py                  ← modules/audit/service.py
│   ├── patient/
│   │   ├── __init__.py
│   │   └── health_alert.py             ← modules/patient/health_alert.py
│   ├── system/
│   │   ├── __init__.py
│   │   ├── quota.py                    ← modules/system/quota.py
│   │   ├── rbac.py                     ← modules/system/rbac.py
│   │   └── settings.py                ← modules/system/settings_service.py
│   └── rag/
│       ├── __init__.py
│       ├── chat_orchestrator.py         新建（从 router_chat.py 抽出）
│       ├── schemas.py                  ← modules/rag/schemas.py
│       └── tasks.py                    ← modules/rag/tasks.py
│
├── ai/                                  新建
│   ├── __init__.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── retrieval.py                ← modules/rag/retrieval.py
│   │   ├── citation.py
│   │   ├── context.py
│   │   ├── compress.py
│   │   ├── query_rewrite.py
│   │   ├── evaluation.py
│   │   ├── ingestion.py
│   │   ├── ingestion_legacy.py
│   │   ├── embeddings.py
│   │   ├── embedding_validation.py
│   │   ├── document_parser.py
│   │   ├── llm_legacy.py
│   │   └── reranker_legacy.py
│   └── agent/                          ← modules/agent/ 整体迁入
│       ├── __init__.py
│       ├── graph.py
│       ├── memory.py
│       ├── security.py
│       ├── state.py
│       └── skills/
│           ├── __init__.py
│           ├── base.py
│           ├── rag_skill.py
│           ├── patient_skills.py
│           ├── calculator_skills.py
│           ├── markdown_loader.py
│           └── custom/
│
├── base/                                ← core/（改名）
│   ├── __init__.py
│   ├── config.py
│   ├── database.py                     ← db/session.py
│   ├── security.py
│   ├── exceptions.py
│   ├── middleware.py
│   ├── snowflake.py
│   └── storage.py
│
├── plugins/                             （不变）
├── tasks/                               （不变，import 更新）
└── telemetry/                           （不变，import 更新）
```

## 5. 技术债清理

### 5.1 chat_service.py 拆解（非合并）

`modules/rag/chat_service.py`（543 行）与 `retrieval.py`（552 行）存在大量重复。

处理方式：**拆解** chat_service.py，而非合并为巨型文件。

| chat_service.py 中的代码 | 去向 |
|-------------------------|------|
| 与 retrieval.py 重复的类型定义（Citation, RetrievedChunk 等） | 删除，统一使用 retrieval.py 的定义 |
| 与 retrieval.py 重复的函数 | 删除 |
| 独有的 chat 流编排逻辑 | → `services/rag/chat_orchestrator.py` |

预计消除约 200 行重复代码。

### 5.2 router_chat.py 瘦身

当前 `router_chat.py`（440 行）承担了路由 + 编排双重职责。

迁移后：
- `routers/rag/chat.py`：~80 行，仅路由定义和请求校验
- `services/rag/chat_orchestrator.py`：~300 行，SSE 流式处理、对话持久化、配额扣减

### 5.3 循环依赖修复

当前 `ai/rag/retrieval.py` 引用 `services/system/quota.redis_client`，形成 ai → services 反向依赖。

修复：将 `redis_client` 工厂移入 `base/`，作为基础设施暴露。

## 6. Import 路径映射

### 批量替换规则（按频率排序）

| 旧路径 | 新路径 | 影响量 |
|--------|--------|--------|
| `from app.db.models` | `from app.models` | 50+ 次 |
| `from app.core.*` | `from app.base.*` | ~29 次 |
| `from app.api.deps` | `from app.routers.deps` | ~18 次 |
| `from app.db.session` | `from app.base.database` | 7 次 |
| `from app.api.api import api_router` | `from app.routers import api_router` | 1 次 |
| `from app.modules.auth.router` | `from app.routers.auth import router` | → |
| `from app.modules.auth.email` | `from app.services.auth.email` | → |
| `from app.modules.audit.*` | `from app.services.audit.*` / `from app.routers.audit.*` | → |
| `from app.modules.patient.router_*` | `from app.routers.patient.*` | → |
| `from app.modules.patient.health_alert` | `from app.services.patient.health_alert` | → |
| `from app.modules.system.router_*` | `from app.routers.system.*` | → |
| `from app.modules.system.quota` | `from app.services.system.quota` | → |
| `from app.modules.system.rbac` | `from app.services.system.rbac` | → |
| `from app.modules.system.settings_service` | `from app.services.system.settings` | → |
| `from app.modules.rag.router_*` | `from app.routers.rag.*` | → |
| `from app.modules.rag.retrieval` | `from app.ai.rag.retrieval` | → |
| `from app.modules.rag.citation` | `from app.ai.rag.citation` | → |
| `from app.modules.rag.chat_service` | `from app.ai.rag.retrieval` / `from app.services.rag.chat_orchestrator` | → |
| `from app.modules.rag.tasks` | `from app.services.rag.tasks` | → |
| `from app.modules.agent.*` | `from app.ai.agent.*` | → |

### Alembic

| 旧 | 新 |
|----|-----|
| env.py 中的 `from app.db.models` | `from app.models` |

### CLI 命令

| 旧 | 新 |
|----|-----|
| `python -m app.db.seed_data` | `python -m app.seed` |

## 7. 不变清单

| 范围 | 保证 |
|------|------|
| 所有 18 个 API URL 路径 | `/api/v1/*` 完全不变 |
| 前端代码 | 零改动 |
| `plugins/` 目录 | 不变 |
| `telemetry/` 目录 | 不变（仅 import 更新） |
| `schemas/` 目录 | 不变 |
| 数据库 schema | 不变 |
| JWT / RLS 逻辑 | 不变 |

## 8. 影响范围

| 类别 | 数量 |
|------|------|
| 移动/改名文件 | ~55 |
| 删除文件 | ~3（chat_service.py + models re-export + 旧 __init__） |
| 新建文件 | ~15（__init__.py + chat_orchestrator.py） |
| 需更新 import 的文件 | ~40 |
| 需更新 Alembic env.py | 1 |
| URL 变更 | 0 |
| 前端改动 | 0 |
| 单元测试 | 全部重写（已清理） |

## 9. 实施计划

### Phase 1：创建目录骨架

创建 `routers/`、`services/`、`ai/`、`base/`、`models/` 五个顶级包及所有子目录的 `__init__.py`。

### Phase 2：文件迁移（git mv）

按第 4 节的迁移清单，使用 `git mv` 保留文件历史。优先级：
1. `db/models/` → `models/`（影响最大，先做先稳定）
2. `core/` → `base/`

3. `api/` → `routers/`
4. `modules/` → `routers/` + `services/` + `ai/`

### Phase 3：Import 替换

按第 6 节映射表执行全局查找替换。

### Phase 4：技术债清理

1. 拆解 chat_service.py
2. 瘦身 router_chat.py → chat.py
3. 新建 chat_orchestrator.py
4. 修复 redis_client 循环依赖

### Phase 5：验证

```bash
# 语法校验
python -c "from app.main import app; print('OK')"

# 启动测试
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 确认路由注册
curl http://localhost:8000/docs

# 更新 AGENTS.md
```

## 10. 后续优化（不在本次范围）

- [ ] `ai/` 中的 DB 操作进一步抽离，使 ai/ 趋近纯计算
- [ ] `ingestion.py` 的 `AsyncSessionLocal()` 改为由 worker 传入
- [ ] `services/` 单文件域视业务扩展决定是否保留子目录
- [ ] 重新生成完整单元测试
- [ ] 更新 AGENTS.md 目录结构文档
