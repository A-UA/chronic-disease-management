# 慢病管理多租户 AI SaaS — 项目指南

更新时间：2026-04-04

## 1. 项目概览

面向慢病管理场景的多租户 AI SaaS 全栈项目，包含后端 API 服务和前端管理后台。

核心能力：

- **慢病管理业务**：患者档案、健康指标录入与趋势分析、管理师分配与管理建议、家属关联与跨组织查看
- **RAG 知识问答**：文档入库 → 检索 → 引用化问答 → 评测闭环
- **企业级工程能力**：多租户隔离 (RLS)、层级 RBAC 权限、组织树穿透、审计日志、配额管理
- **管理后台**：动态菜单路由、仪表盘、患者管理、健康趋势图

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
| **UI 组件库** | Ant Design 5.x + ProComponents |
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
│   │   ├── main.py                    # 应用入口、SnowflakeJSONResponse、中间件注册
│   │   ├── api/
│   │   │   ├── api.py                 # 路由注册中心（18 个端点模块）
│   │   │   ├── deps.py                # 依赖注入：认证、组织上下文、RBAC 权限校验、配额
│   │   │   └── endpoints/             # 业务接口（详见第 3 节）
│   │   ├── core/
│   │   │   ├── config.py              # pydantic-settings 配置（含 RAG 参数）
│   │   │   ├── security.py            # JWT 签发/验证、Argon2 密码哈希
│   │   │   ├── middleware.py          # X-Request-ID 请求追踪中间件
│   │   │   └── snowflake.py           # 雪花 ID 生成器
│   │   ├── db/
│   │   │   ├── models/                # 14 个 ORM 模型文件
│   │   │   │   ├── base.py            # Base、IDMixin、TimestampMixin
│   │   │   │   ├── user.py            # User、PasswordResetToken
│   │   │   │   ├── organization.py    # Organization、OrganizationUser、OrganizationUserRole、OrganizationInvitation、PatientFamilyLink
│   │   │   │   ├── rbac.py            # Resource、Action、Permission、Role、RolePermission、RoleConstraint
│   │   │   │   ├── patient.py         # PatientProfile（JSONB medical_history + GIN 索引）
│   │   │   │   ├── health_metric.py   # HealthMetric（血压/血糖/体重/心率/BMI/SpO2）
│   │   │   │   ├── manager.py         # ManagerProfile、PatientManagerAssignment、ManagementSuggestion
│   │   │   │   ├── menu.py            # Menu（动态菜单树，支持 permission_code 权限过滤）
│   │   │   │   ├── knowledge.py       # KnowledgeBase、Document、Chunk
│   │   │   │   ├── chat.py            # Conversation、Message、UsageLog
│   │   │   │   ├── api_key.py         # ApiKey
│   │   │   │   ├── audit.py           # AuditLog
│   │   │   │   └── settings.py        # SystemSetting
│   │   │   ├── session.py             # AsyncSession 工厂
│   │   │   └── seed_data.py           # 统一种子数据（RBAC + 菜单 + 超管账号）
│   │   ├── schemas/                   # Pydantic 请求/响应模型
│   │   └── services/                  # 业务服务层（16 个文件）
│   ├── alembic/                       # 数据库迁移脚本
│   ├── tests/                         # 自动化测试
│   ├── scripts/                       # 辅助脚本
│   └── pyproject.toml                 # uv 依赖管理
├── frontend/                          # Vite+ Monorepo
│   ├── apps/
│   │   └── website/                   # 管理后台应用
│   │       ├── src/
│   │       │   ├── main.tsx           # React 入口
│   │       │   ├── global.css         # 全局样式重置
│   │       │   ├── api/               # HTTP 客户端与接口封装
│   │       │   │   ├── client.ts      # ky 实例（Token/OrgID 注入、401 拦截）
│   │       │   │   ├── auth.ts        # 登录/用户信息/菜单树
│   │       │   │   ├── dashboard.ts   # 仪表盘统计
│   │       │   │   ├── patients.ts    # 患者 CRUD
│   │       │   │   └── health-metrics.ts  # 健康指标趋势
│   │       │   ├── types/             # TypeScript 类型定义
│   │       │   ├── stores/            # zustand 状态管理
│   │       │   │   └── auth.ts        # 认证状态（token/user/menus/permissions）
│   │       │   ├── hooks/             # 自定义 Hooks
│   │       │   │   └── usePermission.ts   # 权限判断
│   │       │   ├── router/            # 路由系统
│   │       │   │   ├── index.tsx      # 路由入口
│   │       │   │   ├── AuthRoute.tsx  # 登录态守卫
│   │       │   │   ├── generateRoutes.ts  # 菜单 → 路由动态生成
│   │       │   │   └── registry.tsx   # menu code → React 组件注册表
│   │       │   ├── layouts/
│   │       │   │   └── AdminLayout.tsx    # ProLayout 主布局
│   │       │   ├── components/
│   │       │   │   └── PageLoading.tsx    # 全局加载
│   │       │   └── pages/
│   │       │       ├── login/index.tsx        # 登录页
│   │       │       ├── dashboard/index.tsx    # 仪表盘（统计卡片+趋势图）
│   │       │       ├── patients/index.tsx     # 患者列表（ProTable）
│   │       │       ├── patients/[id].tsx      # 患者详情
│   │       │       ├── patients/components/HealthTrendChart.tsx  # 健康趋势图
│   │       │       ├── 403.tsx               # 无权限页
│   │       │       └── 404.tsx               # 未找到页
│   │       ├── vite.config.ts         # Vite 配置（React 插件 + 代理）
│   │       └── tsconfig.json          # TypeScript 配置
│   ├── packages/                      # 共享包（预留）
│   ├── package.json                   # Monorepo 根配置
│   ├── pnpm-workspace.yaml            # pnpm workspace
│   └── vite.config.ts                 # Vite+ 全局配置
├── docker-compose.yml                 # PostgreSQL + Redis + MinIO
└── GEMINI.md                          # 本文件
```

## 3. API 端点总览

18 个路由模块，统一挂载于 `/api/v1` 前缀：

### 认证与身份

| 路由前缀 | 模块 | 核心功能 |
|---------|------|---------|
| `/auth` | `auth.py` | 注册、登录、`/me`（含递归权限）、菜单树（menus 表驱动）、修改密码、密码重置 |
| `/external` | `external_api.py` | API Key 认证的外部接口 |

### 业务资源

| 路由前缀 | 模块 | 核心功能 |
|---------|------|---------|
| `/patients` | `patients.py` | 患者档案 CRUD（含 `/me` 个人视图与管理视图） |
| `/health-metrics` | `health_metrics.py` | 健康指标录入/查询/趋势/修改/删除，含 `/patients/{id}/trend` 管理端趋势接口 |
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
uv run python -m app.db.seed_data     # 初始化种子数据（RBAC + 菜单 + 超管）
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

统一入口：`app/db/seed_data.py`，运行命令 `uv run python -m app.db.seed_data`。

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

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `openai_compatible` | LLM 供应商 |
| `CHAT_MODEL` | `gpt-4o-mini` | 聊天模型 |
| `LLM_BASE_URL` / `LLM_API_KEY` | — | LLM 接口地址和密钥 |
| `EMBEDDING_PROVIDER` | `openai` | Embedding 供应商（推荐 `zhipu`） |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding 模型 |
| `RERANKER_PROVIDER` | `noop` | Reranker 供应商 |

### RAG 参数

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RAG_VECTOR_WEIGHT` | `0.7` | 向量检索权重 |
| `RAG_KEYWORD_WEIGHT` | `0.3` | 关键词检索权重 |
| `RAG_RRF_K` | `60` | RRF 融合参数 |
| `RAG_ENABLE_CONTEXTUAL_INGESTION` | `false` | 入库背景增强 |

### 其他

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WORKER_ID` | — | 雪花算法节点 ID (0-1023) |
| `CORS_ORIGINS` | `localhost:3000,5173` | 跨域来源 |
| `MAX_UPLOAD_SIZE_MB` | `50` | 最大上传大小 |
| `DEBUG_SQL` | `false` | SQL 日志 |

## 9. 开发约定

### 后端

- **ID 使用**：所有新表必须继承 `IDMixin`，默认生成 64 位雪花 ID
- **类型提示**：ID 字段在 Python 中一律使用 `int` 类型
- **接口返回**：直接返回 `int`，`SnowflakeJSONResponse` 自动处理 JS 精度转换
- **API 设计**：新增功能优先走 Provider / Service 抽象
- **导入规范**：不要在导入阶段初始化外部服务（延迟初始化模式）
- **权限控制**：管理类接口使用 `check_permission("resource:action")` 依赖注入
- **组织隔离**：涉及租户数据的端点必须注入 `get_current_org` 并校验 `org_id`
- **审计日志**：敏感操作需调用 `audit_action()` 记录
- **种子数据**：所有预制数据统一写入 `app/db/seed_data.py`
- **终端环境**：使用 PowerShell，命令用 `;` 分隔（不是 `&&`），注意 stderr 的 INFO 日志会导致假性 exit code 1

### 前端

- **Vite+ 工具链**：所有操作用 `vp` 命令，不直接使用 pnpm/npm
- **导入来源**：从 `vite-plus` 导入而非直接 `vite` / `vitest`
- **路径别名**：`@/` 映射到 `src/`，tsconfig 中用 `"./src/*"` 而非 `"src/*"`
- **tsconfig 规范**：不使用 `baseUrl`（Vite+ tsgolint 已移除支持）
- **异步规范**：`navigate()` 等返回 Promise 的函数需加 `void` 前缀
- **新增页面**：在 `pages/` 创建组件 → 在 `router/registry.tsx` 注册 menu code 映射
- **提交前检查**：pre-commit hook 自动运行 `vp check --fix`

## 10. 待办事项

- [ ] 接入真实 Embedding Provider（推荐智谱 `embedding-3`）
- [ ] Reranker 从 `noop` 切换到实际 Provider
- [ ] 前端：知识库管理模块
- [ ] 前端：成员管理与角色权限模块
- [ ] 前端：AI 问答对话界面（SSE 流式）
- [ ] 前端：操作审计日志查看
- [ ] 密码重置邮件接入 SMTP
- [ ] 审计日志异步化（当前同步写入）
- [ ] 健康指标异常告警逻辑
- [ ] 多轮对话压缩与专项评测
