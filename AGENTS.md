# 慢病管理多租户 AI SaaS — 项目指南

更新时间：2026-04-07

## 1. 项目概览

面向慢病管理场景的多租户 AI SaaS 全栈项目，包含后端 API 服务和前端管理后台。

核心能力：

- **慢病管理业务**：患者档案、健康指标录入与趋势分析、管理师分配与管理建议、家属关联与跨组织查看
- **RAG 知识问答**：文档入库 → 检索 → 引用化问答 → 评测闭环
- **企业级工程能力**：多租户隔离 (RLS)、层级 RBAC 权限、组织树穿透、审计日志、配额管理
- **管理后台**：动态菜单路由、仪表盘、患者管理、健康趋势图、知识库管理、AI 问答、成员管理、审计日志

### 技术栈

| 层级 | 技术选型 |
|------|---------|
| **后端框架** | FastAPI |
| **ORM** | SQLAlchemy 2.x Async（`BigInteger` 主键 + `IDMixin`） |
| **数据库** | PostgreSQL + pgvector（RLS 行级安全策略） |
| **序列化** | orjson（高性能 JSON，自动大整数精度保护） |
| **缓存/限流** | Redis（延迟初始化，组织树缓存） |
| **对象存储** | MinIO |
| **ID 体系** | Snowflake ID 64-bit（`snowflake-id-toolkit`） |
| **密码哈希** | Argon2（`passlib[argon2]` + `argon2-cffi`） |
| **LLM/Embedding** | OpenAI 兼容接口（支持小米 MiMo、智谱等多 Provider） |
| **文档解析** | PyMuPDF + pdfplumber + pytesseract |
| **Token 计数** | tiktoken |
| **异步任务** | arq |
| **测试** | pytest / pytest-asyncio / httpx |
| **数据库迁移** | Alembic |
| **前端框架** | React 19 + TypeScript 5.x |
| **前端构建** | Vite+ (Vite 8 / Rolldown) monorepo |
| **CSS 框架** | Tailwind CSS 4.x（`@tailwindcss/vite` 插件集成，自定义 design token） |
| **UI 组件库** | Ant Design 6.x + ProComponents |
| **状态管理** | zustand |
| **HTTP 客户端** | ky |
| **数据请求** | TanStack React Query |
| **图表** | @ant-design/charts |
| **包管理** | pnpm（由 Vite+ `vp` 命令统一管理） |

## 2. 目录结构

```
chronic-disease-management/
├── backend/
│   ├── app/
│   │   ├── main.py                    # 应用入口、SnowflakeJSONResponse、Telemetry + 插件初始化
│   │   ├── seed.py                    # 统一种子数据（RBAC + 菜单 + 超管账号）
│   │   ├── base/                      # 基础设施层（原 core/ + db/session）
│   │   │   ├── config.py              # pydantic-settings 配置（含 RAG + OTel + arq 参数）
│   │   │   ├── exceptions.py          # 统一业务异常
│   │   │   ├── security.py            # JWT 签发/验证、Argon2 密码哈希
│   │   │   ├── middleware.py          # X-Request-ID 请求追踪中间件
│   │   │   ├── snowflake.py           # 雪花 ID 生成器
│   │   │   ├── storage.py             # MinIO 对象存储
│   │   │   └── database.py            # AsyncSession 工厂（原 db/session.py）
│   │   ├── models/                    # ORM 模型层（原 db/models/）
│   │   │   ├── base.py                # Base + IDMixin + TimestampMixin
│   │   │   ├── user.py, tenant.py, organization.py, rbac.py, menu.py
│   │   │   ├── patient.py, health_metric.py, manager.py
│   │   │   ├── knowledge.py, chat.py, audit.py, settings.py, api_key.py
│   │   │   └── __init__.py            # 统一 re-export 所有模型
│   │   ├── routers/                   # HTTP 路由层（薄适配器）
│   │   │   ├── __init__.py            # 路由注册中心 api_router
│   │   │   ├── deps.py                # 依赖注入：认证、RLS、RBAC、配额
│   │   │   ├── auth/router.py         # 认证路由
│   │   │   ├── audit/router.py        # 审计日志路由
│   │   │   ├── patient/               # 患者路由（patients/health_metrics/family/managers）
│   │   │   ├── system/                # 系统路由（10 个：dashboard/organizations/users/rbac/...）
│   │   │   └── rag/                   # RAG 路由（chat/conversations/documents/knowledge_bases）
│   │   ├── services/                  # 业务编排层
│   │   │   ├── auth/email.py          # 邮件服务
│   │   │   ├── audit/service.py       # 审计日志服务（audit_action / fire_audit）
│   │   │   ├── patient/health_alert.py # 健康指标告警
│   │   │   ├── system/                # 系统服务（quota.py / rbac.py / settings.py）
│   │   │   └── rag/                   # RAG 服务（schemas.py / tasks.py）
│   │   ├── ai/                        # AI 领域层
│   │   │   ├── rag/                   # RAG 计算引擎
│   │   │   │   ├── retrieval.py        # 混合检索管线（向量+关键词+RRF+Rerank）
│   │   │   │   ├── ingestion.py        # 文档入库管线
│   │   │   │   ├── citation.py         # 引用构建
│   │   │   │   ├── context.py          # 对话上下文增强
│   │   │   │   ├── compress.py         # 多轮对话历史压缩
│   │   │   │   ├── query_rewrite.py    # 查询改写
│   │   │   │   └── evaluation.py       # RAG 评估
│   │   │   └── agent/                 # AI Agent（LangGraph 状态机 + Skills）
│   │   │       ├── graph.py, state.py, memory.py, security.py
│   │   │       └── skills/            # 工具技能（patient/rag/calculator/markdown）
│   │   ├── plugins/                   # AI 插件体系（配置驱动 + 延迟初始化）
│   │   │   ├── registry.py            # PluginRegistry 统一注册中心
│   │   │   ├── llm/                   # LLM 插件
│   │   │   ├── embedding/             # Embedding 插件
│   │   │   ├── reranker/              # Reranker 插件
│   │   │   ├── parser/                # 文档解析器插件
│   │   │   └── chunker/               # 切块策略插件
│   │   ├── tasks/                     # arq 异步任务队列
│   │   │   └── worker.py              # arq Worker 配置
│   │   ├── telemetry/                 # 可观测性基础设施
│   │   │   ├── setup.py, tracing.py, logging.py
│   │   └── schemas/                   # Pydantic 请求/响应模型
│   ├── alembic/                       # 数据库迁移脚本
│   ├── tests/                         # 自动化测试
│   ├── scripts/                       # 辅助脚本
│   └── pyproject.toml                 # uv 依赖管理
├── frontend/                          # Vite+ Monorepo（结构不变）
│   ├── apps/website/src/              # 管理后台应用
│   ├── packages/                      # 共享包（预留）
│   └── vite.config.ts                 # Vite+ 全局配置
├── docker-compose.yml                 # PostgreSQL + Redis + MinIO
└── AGENTS.md                          # 本文件
```

### 架构分层（依赖方向：routers → services → ai → models → base）

| 层级 | 目录 | 职责 | 禁止 |
|------|------|------|------|
| **路由层** | `routers/` | HTTP 适配、参数校验、依赖注入 | 禁止写 DB 查询 |
| **服务层** | `services/` | 业务编排、事务管理、配额、审计 | 禁止直接调 LLM |
| **AI 层** | `ai/` | 检索、Prompt、Agent 状态机 | 禁止自建 session |
| **模型层** | `models/` | ORM 定义 | 禁止业务逻辑 |
| **基础层** | `base/` | 配置、安全、数据库连接 | 禁止反向依赖 |

## 3. API 端点总览

18 个路由模块，统一挂载于 `/api/v1` 前缀：

### 认证与身份

| 路由前缀 | 模块 | 核心功能 |
|---------|------|---------|
| `/auth` | `auth.py` | 注册、登录（含多部门选择）、`/me`、菜单树、`/select-org`、`/switch-org`、`/my-orgs`、修改密码、SMTP 密码重置 |
| `/external` | `external_api.py` | API Key 认证的外部接口 |

### 业务资源

| 路由前缀 | 模块 | 核心功能 |
|---------|------|---------|
| `/patients` | `patients.py` | 患者档案 CRUD（含 `/me` 个人视图与管理视图） |
| `/health-metrics` | `health_metrics.py` | 健康指标录入（含异常告警检测）/查询/趋势/修改/删除 |
| `/family` | `family.py` | 家属关联创建/查看/解绑、跨组织查看 |
| `/managers` | `managers.py` | 管理师档案 CRUD、患者分配/取消、管理建议 CRUD |
| `/chat` | `chat.py` | RAG 对话（SSE 流式）、配额校验、引用抽取 |
| `/conversations` | `conversations.py` | 对话管理（列表/详情/删除） |
| `/documents` | `documents.py` | 文档上传/管理/状态 |
| `/kb` | `knowledge_bases.py` | 知识库 CRUD + 统计 |

### 组织与权限

| 路由前缀 | 模块 | 核心功能 |
|---------|------|---------|
| `/organizations` | `organizations.py` | 机构管理、成员管理、邀请 |
| `/users` | `users.py` | 用户管理 |
| `/rbac` | `rbac.py` | 角色/权限/约束管理 |
| `/dashboard` | `dashboard.py` | 统计仪表盘（平台级 & 租户级） |
| `/audit-logs` | `audit_logs.py` | 审计日志查询 |
| `/usage` | `usage.py` | 使用量/配额查询 |
| `/settings` | `settings.py` | 动态系统设置 |
| `/api-keys` | `api_keys.py` | API Key 管理 |

## 4. 数据模型概览

### 核心实体关系

```
Organization（组织，树形自引用 parent_id）
 ├── OrganizationUser（多对多：用户 <-> 组织，user_type: staff/patient）
 │   └── OrganizationUserRole（多对多：组织用户 <-> 角色）
 ├── PatientProfile（患者档案，JSONB medical_history + GIN 索引）
 │   ├── HealthMetric（健康指标：六类，复合索引 patient+type+time）
 │   ├── PatientManagerAssignment（管理师分配：main/assistant）
 │   ├── PatientFamilyLink（家属关联：relationship_type + access_level）
 │   └── ManagementSuggestion（管理建议：clinical/lifestyle/general）
 ├── ManagerProfile（管理师档案）
 ├── KnowledgeBase → Document → Chunk（知识库 → 文档 → 切块）
 ├── Conversation → Message（对话 → 消息，含 metadata_ JSONB）
 └── UsageLog（使用量日志）

Menu（菜单树，支持 permission_code 关联 RBAC 权限）

Role（角色，支持继承 parent_role_id + 组织隔离 org_id）
 └── Permission（权限点：resource:action 格式，纯 API 类型）
     └── Resource + Action（资源-操作解耦）
```

### RBAC 权限体系

**角色层级**（继承式，子角色自动拥有父角色全部权限）：

```
staff (基础成员)
 └── manager (管理人员)
      └── admin (管理员)
           └── owner (所有者)
```

**权限清单**（12 个纯 API 权限）：

| 权限编码 | 说明 | staff | manager | admin | owner |
|---------|------|:-----:|:-------:|:-----:|:-----:|
| `patient:read` | 查看患者 | * | * | * | * |
| `patient:create` | 创建患者 | | * | * | * |
| `patient:update` | 修改患者 | | * | * | * |
| `patient:delete` | 删除患者 | | | * | * |
| `suggestion:read` | 查看建议 | * | * | * | * |
| `suggestion:create` | 创建建议 | | * | * | * |
| `chat:use` | AI 对话 | * | * | * | * |
| `kb:manage` | 管理知识库 | | | * | * |
| `doc:manage` | 管理文档 | | | * | * |
| `org_member:manage` | 管理成员 | | | * | * |
| `org_usage:read` | 查看使用量 | | | * | * |
| `audit_log:read` | 查看审计 | | | * | * |

**菜单可见性**：由 `menus` 表的 `permission_code` 字段控制，不在角色中分配菜单权限。用户拥有某 API 权限即可看到关联菜单。

### 预制超管账号

| 项 | 值 |
|---|---|
| 邮箱 | `admin@cdm.local` |
| 密码 | `Admin@2026` |
| 角色 | `owner`（继承全部权限） |
| 组织 | 默认组织（enterprise 套餐） |

## 5. 前端架构

### 核心设计

- **动态路由**：后端 `GET /auth/menu-tree` 返回菜单树 → `generateRoutes.ts` 递归生成 React Router 路由 → `registry.tsx` 将 menu code 映射到 React 组件
- **认证守卫**：`AuthRoute.tsx` 检查 token，未登录跳转 `/login`，已登录自动拉取用户信息和菜单
- **权限控制**：`usePermission` Hook 判断按钮级权限（如删除按钮仅 `patient:delete` 可见）
- **请求拦截**：ky 客户端自动注入 `Authorization` 和 `X-Organization-ID`，401 自动登出

### 样式体系：Tailwind CSS 4.x + 自定义 Design Token

项目使用 **Tailwind CSS 4.x**（通过 `@tailwindcss/vite` Vite 插件集成），采用 utility-first 方案编写样式。

**集成方式**：
- `vite.config.ts` 中注册 `@tailwindcss/vite` 插件
- `global.css` 中通过 `@import "tailwindcss"` 引入，并在 `@theme` 块中定义自定义 design token
- Tailwind v4 不再需要 `tailwind.config.js`，所有配置（包括自定义主题 token）直接写在 CSS 中

**自定义 Design Token 规范**（遵循 shadcn/ui 命名约定）：
- 在 `global.css` 的 `@theme` 块中定义项目级 token，采用 `{role}` / `{role}-foreground` 配对模式
- 核心 token 清单：
  - **基础**：`--background` / `--foreground`
  - **卡片**：`--card` / `--card-foreground`
  - **弹层**：`--popover` / `--popover-foreground`
  - **主色**：`--primary` / `--primary-foreground`
  - **辅色**：`--secondary` / `--secondary-foreground`
  - **柔和**：`--muted` / `--muted-foreground`
  - **强调**：`--accent` / `--accent-foreground`
  - **危险**：`--destructive` / `--destructive-foreground`
  - **边框/输入/环**：`--border`、`--input`、`--ring`
  - **圆角**：`--radius`
  - **图表**：`--chart-1` ~ `--chart-5`
  - **侧边栏**：`--sidebar-*` 系列（可选）
- 定义后可直接在 Tailwind utility class 中使用，如 `bg-primary`、`text-muted-foreground`、`border-border`

**Ant Design 兼容**：
- `global.css` 中 `@layer base` 做了最小化重置，避免 Tailwind preflight 破坏 antd 组件样式
- antd 组件内部样式依然由 antd 自身管理，自定义布局和页面样式用 Tailwind utility class

### 已实现页面

| 页面 | 路径 | 功能 |
|------|------|------|
| 登录页 | `/login` | 渐变背景 + 卡片表单 |
| 仪表盘 | `/dashboard` | 7 统计卡片 + Token 趋势折线图 |
| 患者列表 | `/patients` | ProTable + 搜索/分页/权限按钮 |
| 患者详情 | `/patients/:id` | 基本信息 + 多指标健康趋势图（血压双线） |
| 403 | — | 无权限 |
| 404 | — | 未找到 |

## 6. 本地开发

### 启动基础设施

```bash
docker compose up -d
```

服务列表：
- PostgreSQL (pgvector v0.5.1) — `localhost:5432`
- Redis 7 — `localhost:6379`
- MinIO — `localhost:9000`（控制台 `localhost:9001`）

### 后端

```bash
cd backend
uv sync                              # 安装依赖
uv run alembic upgrade head           # 数据库迁移
uv run python -m app.seed             # 初始化种子数据（RBAC + 菜单 + 超管）
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
vp install                            # 安装依赖（等同 pnpm install）
vp dev                                # 启动开发服务器 → http://localhost:5173
vp check                              # 格式化 + lint + 类型检查
vp build                              # 生产构建
```

> **重要**：前端使用 Vite+ 工具链，所有操作通过 `vp` 命令执行，不要直接使用 pnpm/npm。

### 服务地址

| 服务 | 地址 |
|------|------|
| 后端 API | `http://localhost:8000` |
| API 文档 | `http://localhost:8000/docs` |
| 前端管理后台 | `http://localhost:5173` |
| 前端代理 | `/api/*` → `localhost:8000` |

## 7. 种子数据

统一入口：`app/seed.py`，运行命令 `uv run python -m app.seed`。

在同一个事务中依次完成：

1. **RBAC 初始化**：8 资源 + 6 操作 + 12 权限 + 4 层级角色
2. **菜单初始化**：7 一级菜单 + 5 二级菜单（permission_code 对齐 RBAC 权限）
3. **超管账号**：默认组织 + 超管用户 + owner 角色绑定

全部幂等设计，可重复执行不会重复创建。

## 8. 配置约定

主要环境变量位于 `backend/.env`，参考模板 `backend/.env.example`。

### 必填项

| 变量 | 说明 |
|------|------|
| `JWT_SECRET` | JWT 签名密钥（启动时强制校验） |
| `API_KEY_SALT` | API Key 哈希盐值（启动时强制校验） |

### LLM / Embedding / Reranker

> **注意**：`LLM_PROVIDER` 和 `EMBEDDING_PROVIDER` 已废弃（插件系统自动选择 `openai_compatible` 实现）。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CHAT_MODEL` | `gpt-4o-mini` | 聊天模型 |
| `LLM_BASE_URL` / `LLM_API_KEY` | — | LLM 接口地址和密钥 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding 模型 |
| `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY` | — | 留空则回退到 LLM_* |
| `RERANKER_PROVIDER` | `noop` | Reranker 供应商（支持 `noop`/`simple`/`openai_compatible`） |

### RAG 参数

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RAG_VECTOR_WEIGHT` | `0.7` | 向量检索权重 |
| `RAG_KEYWORD_WEIGHT` | `0.3` | 关键词检索权重 |
| `RAG_RRF_K` | `60` | RRF 融合参数 |
| `RAG_ENABLE_CONTEXTUAL_INGESTION` | `false` | 入库背景增强 |

### OpenTelemetry（可选）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OTLP_ENDPOINT` | （空） | OTLP gRPC 导出地址（不设则 noop） |
| `OTEL_SERVICE_NAME` | `cdm-backend` | 服务名称 |

### arq Worker

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ARQ_MAX_JOBS` | `10` | Worker 最大并发任务数 |
| `ARQ_JOB_TIMEOUT` | `600` | 单任务超时（秒） |

### 其他

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WORKER_ID` | — | 雪花算法节点 ID (0-1023) |
| `CORS_ORIGINS` | `localhost:3000,5173` | 跨域来源 |
| `MAX_UPLOAD_SIZE_MB` | `50` | 最大上传大小 |
| `DEBUG_SQL` | `false` | SQL 日志 |

## 9. 开发约定

### 后端

- **三层架构**：`routers/`（HTTP 适配）→ `services/`（业务编排）→ `ai/`（AI 计算），依赖严格单向
- **ID 使用**：所有新表必须继承 `IDMixin`，默认生成 64 位雪花 ID
- **类型提示**：ID 字段在 Python 中一律使用 `int` 类型
- **接口返回**：直接返回 `int`，`SnowflakeJSONResponse` 自动处理 JS 精度转换
- **插件体系**：新增 AI 能力优先通过 `PluginRegistry` 注册插件实现（`app/plugins/`）
- **路由注册**：`routers/__init__.py` 为路由注册中心，新增路由在对应子目录创建后在此注册
- **依赖注入**：`routers/deps.py` 提供认证、RLS、RBAC 等依赖，从 `app.routers.deps` 导入
- **基础设施**：配置从 `app.base.config` 导入，安全从 `app.base.security`，数据库从 `app.base.database`
- **模型导入**：从 `app.models` 导入（如 `from app.models import User, Patient`）
- **服务调用**：审计用 `app.services.audit.service`，配额用 `app.services.system.quota`
- **AI 调用**：检索用 `app.ai.rag.retrieval`，Agent 用 `app.ai.agent`
- **导入规范**：不要在导入阶段初始化外部服务（延迟初始化模式）
- **权限控制**：管理类接口使用 `check_permission("resource:action")` 依赖注入
- **认证架构**：JWT 内嵌 tenant_id/org_id/roles，前端不解析 JWT，权限通过 `/auth/me` 获取
- **组织隔离**：涉及租户数据的端点必须注入 `inject_rls_context`，RLS 策略在数据库层强制隔离
- **审计日志**：敏感操作可用 `audit_action()`（事务内同步）或 `fire_audit()`（即发即忘异步）
- **可观测性**：核心管线使用 `trace_span` / `@traced` 添加 OTel 链路追踪
- **种子数据**：所有预制数据统一写入 `app/seed.py`
- **终端环境**：使用 PowerShell，命令用 `;` 分隔（不是 `&&`），注意 stderr 的 INFO 日志会导致假性 exit code 1

### 前端

- **Vite+ 工具链**：所有操作用 `vp` 命令，不直接使用 pnpm/npm
- **导入来源**：从 `vite-plus` 导入而非直接 `vite` / `vitest`
- **路径别名**：`@/` 映射到 `src/`，tsconfig 中用 `"./src/*"` 而非 `"src/*"`
- **tsconfig 规范**：不使用 `baseUrl`（Vite+ tsgolint 已移除支持）
- **异步规范**：`navigate()` 等返回 Promise 的函数需加 `void` 前缀
- **新增页面**：在 `pages/` 创建组件 → 在 `router/registry.tsx` 注册 menu code 映射
- **提交前检查**：pre-commit hook 自动运行 `vp check --fix`
- **样式编写**：优先使用 Tailwind utility class（如 `className="flex items-center gap-4 rounded-lg bg-primary text-primary-foreground"`），避免手写自定义 CSS
- **自定义 Token**：新增 design token 统一在 `global.css` 的 `@theme` 块中定义，命名遵循 shadcn `{role}/{role}-foreground` 配对规范，不要在组件内 inline 定义 CSS 变量
- **Tailwind 配置**：Tailwind v4 无需 `tailwind.config.js`，所有主题扩展写在 `global.css` 的 `@theme` 中
- **antd 样式兼容**：不要用 Tailwind 覆盖 antd 组件内部样式；antd 组件的定制通过 ConfigProvider theme token 实现

## 10. 已完成事项

- [x] 接入真实 Embedding Provider（zhipu 代码就绪，需 `.env` 配置）
- [x] Reranker 新增 `zhipu` Provider
- [x] PostgreSQL RLS 策略（17 + 2 + 1 表全覆盖）
- [x] 前端：知识库管理模块
- [x] 前端：成员管理与角色权限模块
- [x] 前端：AI 问答对话界面（SSE 流式）
- [x] 前端：操作审计日志查看
- [x] 前端：多部门登录 + 部门切换
- [x] 密码重置邮件接入 SMTP（降级兼容日志模式）
- [x] 审计日志异步化（`fire_audit` 即发即忘）
- [x] 健康指标异常告警逻辑（血压/血糖/心率/血氧/BMI）
- [x] 多轮对话压缩（LLM 摘要 + 最近消息保留）
- [x] 后端模块化重构：6 个业务模块 + 5 个 AI 插件族 + PluginRegistry
- [x] 三层架构重构：routers/services/ai 分离，modules/ → 三层目录，core/ → base/，db/ → models/ + base/database
- [x] OpenTelemetry 可观测性基础设施（trace_span / @traced / setup_telemetry）
- [x] arq 异步任务队列（Worker 配置 + 文档入库/审计日志任务）
- [x] 引用逻辑拆分（citation.py 独立模块）

## 11. 测试覆盖

```
后端：234 tests passed（模块层 + API 层 + 服务层 + RLS + 插件注册 + Telemetry）
前端：vp check — 39 files, 0 error, 0 warning
```
