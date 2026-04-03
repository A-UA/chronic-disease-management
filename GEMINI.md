# 慢病管理多租户 AI SaaS 后端 — 项目指南

更新时间：2026-04-03

## 1. 项目概览

本项目是一个面向慢病管理场景的多租户 AI SaaS 后端，以 FastAPI 为基础框架，核心能力包括：

- **慢病管理业务**：患者档案、健康指标录入与趋势分析、管理师分配与管理建议、家属关联与跨组织查看
- **RAG 知识问答**：文档入库 → 检索 → 引用化问答 → 评测闭环
- **企业级工程能力**：多租户隔离 (RLS)、层级 RBAC 权限、组织树穿透、审计日志、配额管理

### 技术栈

| 层级         | 技术选型                                              |
|------------|---------------------------------------------------|
| 后端框架     | FastAPI                                             |
| ORM        | SQLAlchemy 2.x Async（`BigInteger` 主键 + `IDMixin`） |
| 数据库     | PostgreSQL + pgvector（RLS 行级安全策略）               |
| 序列化     | orjson（高性能 JSON，自动大整数精度保护）                  |
| 缓存/限流  | Redis（延迟初始化，组织树缓存）                           |
| 对象存储   | MinIO                                               |
| ID 体系    | Snowflake ID 64-bit（`snowflake-id-toolkit`）         |
| 密码哈希   | Argon2（`passlib[argon2]` + `argon2-cffi`）           |
| LLM/Embedding | OpenAI 兼容接口（支持小米 MiMo、智谱等多 Provider）    |
| 文档解析   | PyMuPDF + pdfplumber + pytesseract                   |
| Token 计数 | tiktoken                                             |
| 异步任务   | arq                                                  |
| 测试       | pytest / pytest-asyncio / httpx                      |
| 数据库迁移 | Alembic                                              |

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
│   │   │   ├── middleware.py           # X-Request-ID 请求追踪中间件
│   │   │   └── snowflake.py           # 雪花 ID 生成器
│   │   ├── db/
│   │   │   ├── models/                # 13 个 ORM 模型文件
│   │   │   │   ├── base.py            # Base、IDMixin、TimestampMixin
│   │   │   │   ├── user.py            # User、PasswordResetToken
│   │   │   │   ├── organization.py    # Organization、OrganizationUser、OrganizationUserRole、OrganizationInvitation、PatientFamilyLink
│   │   │   │   ├── rbac.py            # Resource、Action、Permission、Role、RolePermission、RoleConstraint
│   │   │   │   ├── patient.py         # PatientProfile（JSONB medical_history + GIN 索引）
│   │   │   │   ├── health_metric.py   # HealthMetric（血压/血糖/体重/心率/BMI/SpO2）
│   │   │   │   ├── manager.py         # ManagerProfile、PatientManagerAssignment、ManagementSuggestion
│   │   │   │   ├── knowledge.py       # KnowledgeBase、Document、Chunk
│   │   │   │   ├── chat.py            # Conversation、Message、UsageLog
│   │   │   │   ├── api_key.py         # ApiKey
│   │   │   │   ├── audit.py           # AuditLog
│   │   │   │   └── settings.py        # SystemSetting
│   │   │   ├── session.py             # AsyncSession 工厂
│   │   │   └── seed_rbac.py           # RBAC 种子数据（资源/操作/权限/角色层级）
│   │   ├── schemas/                   # Pydantic 请求/响应模型（7 个文件）
│   │   └── services/                  # 业务服务层（16 个文件，详见第 4 节）
│   ├── alembic/                       # 24 个迁移脚本
│   ├── tests/                         # 自动化测试
│   │   ├── api/                       # 8 个 API 测试文件
│   │   └── services/                  # 7 个服务测试文件
│   ├── scripts/                       # 辅助脚本
│   │   ├── sync_permissions.py        # 权限同步脚本
│   │   ├── evaluate_rag.py            # RAG 评测脚本
│   │   ├── validate_embeddings.py     # 向量验证脚本
│   │   └── cleanup_mixins.py          # Mixin 清理脚本
│   └── pyproject.toml                 # uv 依赖管理
├── docker-compose.yml                 # PostgreSQL(pgvector) + Redis + MinIO
└── GEMINI.md                          # 本文件
```

## 3. API 端点总览

18 个路由模块，统一挂载于 `/api/v1` 前缀：

### 认证与身份

| 路由前缀       | 模块                     | 核心功能                                                      |
|-------------|------------------------|-----------------------------------------------------------|
| `/auth`     | `auth.py`              | 注册、登录、`/me`（含递归权限）、菜单树、修改密码、密码重置（验证码） |
| `/external` | `external_api.py`      | API Key 认证的外部接口                                        |

### 业务资源

| 路由前缀           | 模块                     | 核心功能                                                                                                    |
|-----------------|------------------------|---------------------------------------------------------------------------------------------------------|
| `/patients`     | `patients.py`          | 患者档案 CRUD（含 `/me` 个人视图与管理视图）、管理建议查看、管理员创建/删除档案                                        |
| `/health-metrics` | `health_metrics.py`  | 健康指标录入/查询/趋势/修改/删除（支持 blood_pressure, blood_sugar, weight, heart_rate, bmi, spo2 六类）          |
| `/family`       | `family.py`            | 家属关联创建/查看/解绑、跨组织查看关联患者档案（含审计日志）                                                        |
| `/managers`     | `managers.py`          | 管理师档案 CRUD、患者分配/取消分配、管理建议创建/修改/删除                                                           |
| `/chat`         | `chat.py`              | RAG 对话（SSE 流式）、配额校验、语义级引用抽取、对话历史 Token 预算加载                                              |
| `/conversations` | `conversations.py`    | 对话管理（列表/详情/删除等）                                                                                    |
| `/documents`    | `documents.py`         | 文档上传/管理/状态                                                                                            |
| `/kb`           | `knowledge_bases.py`   | 知识库 CRUD + 统计（文档数/chunk 数/token 数）                                                                 |

### 组织与权限

| 路由前缀           | 模块                     | 核心功能                                                          |
|-----------------|------------------------|---------------------------------------------------------------|
| `/organizations` | `organizations.py`    | 机构列表/创建/编辑、成员管理、邀请（发起/接受/列出）                     |
| `/users`        | `users.py`             | 用户管理                                                          |
| `/rbac`         | `rbac.py`              | 角色/权限/约束管理                                                  |
| `/dashboard`    | `dashboard.py`         | 统计仪表盘（支持平台级全量 & 租户级组织树聚合）                          |
| `/audit-logs`   | `audit_logs.py`        | 审计日志查询                                                      |
| `/usage`        | `usage.py`             | 使用量/配额查询                                                    |
| `/settings`     | `settings.py`          | 动态系统设置（Redis 缓存 + DB 持久化）                               |
| `/api-keys`     | `api_keys.py`          | API Key 管理（HMAC 哈希存储、过期校验、QPS 限流、Token 配额）         |

## 4. 服务层架构

### 慢病管理核心

- `services/audit.py` — 审计日志记录（异步友好，不强制 commit）
- `services/rbac.py` — RBAC 服务：递归 CTE 角色继承、有效权限聚合、SSD 冲突检测
- `services/settings.py` — 动态设置服务：Redis 缓存 + DB fallback + Pydantic 类型自动转换
- `services/quota.py` — 配额管理：Redis 优先 + DB 回退、流式配额检查

### RAG 知识问答链路

| 服务文件                      | 职责                                                       |
|---------------------------|----------------------------------------------------------|
| `document_parser.py`      | 文档解析（txt / docx / pdf，含 PyMuPDF + pytesseract OCR）   |
| `rag_ingestion.py`        | 文档切块与入库（含 Token 计数、contextual ingestion 可选开关） |
| `chat.py`                 | 检索 + Prompt 构建 + 引用抽取 + 结构化 statement-citation    |
| `query_rewrite.py`        | 查询规范化 + 医疗同义词扩展 + 规则重写 + LLM 语义重写        |
| `conversation_context.py` | 多轮对话上下文增强（追问型查询拼接历史）                       |
| `embeddings.py`           | Embedding Provider 抽象（OpenAI 兼容 / 智谱 / noop）        |
| `llm.py`                  | LLM Provider 抽象（流式 / 非流式文本生成）                   |
| `reranker.py`             | Reranker Provider 抽象（OpenAI 兼容 / noop）                |
| `provider_registry.py`    | 全局 Provider 单例注册表（延迟初始化）                        |
| `rag_evaluation.py`       | 离线评测（Recall / Match Rate / Latency 等多维指标）         |
| `embedding_validation.py` | 向量完整性验证                                               |
| `storage.py`              | MinIO 对象存储服务（延迟初始化）                              |

## 5. 数据模型概览

### 核心实体关系

```
Organization（组织，树形自引用 parent_id）
 ├── OrganizationUser（多对多：用户 ↔ 组织，user_type: staff/patient）
 │   └── OrganizationUserRole（多对多：组织用户 ↔ 角色）
 ├── PatientProfile（患者档案，JSONB medical_history + GIN 索引）
 │   ├── HealthMetric（健康指标：六类，复合索引 patient+type+time）
 │   ├── PatientManagerAssignment（管理师分配：main/assistant）
 │   ├── PatientFamilyLink（家属关联：relationship_type + access_level）
 │   └── ManagementSuggestion（管理建议：clinical/lifestyle/general）
 ├── ManagerProfile（管理师档案）
 ├── KnowledgeBase → Document → Chunk（知识库 → 文档 → 切块）
 ├── Conversation → Message（对话 → 消息，含 metadata_ JSONB）
 └── UsageLog（使用量日志）

Role（角色，支持继承 parent_role_id + 组织隔离 org_id）
 └── Permission（权限点：resource:action 格式，type: api/menu/element）
     └── Resource + Action（资源-操作解耦）
         └── RoleConstraint（SSD 责任分离约束）
```

### 预置角色层级

```
staff (基础成员)
 └── manager (管理人员) — 继承 staff 全部权限
      └── admin (管理员) — 继承 manager 全部权限
           └── owner (所有者) — 继承 admin 全部权限
```

另有 `platform_admin` / `platform_viewer` 作为平台级角色（org_id 为 NULL）。

## 6. 工程能力详情

### ID 与精度保护

- 全表使用 `IDMixin` 生成 Snowflake ID（64-bit），`Base.type_annotation_map` 全局映射 `int → BigInteger`
- `SnowflakeJSONResponse`（继承 `ORJSONResponse`）在序列化前递归转换超过 JS 安全范围的整数为字符串
- `HTTPException` 和 `RequestValidationError` 的异常处理器也经过大整数保护包装

### 多租户数据隔离

- **RLS (Row-Level Security)**：PostgreSQL 行级安全策略，通过 `set_config('app.current_org_id')` / `set_config('app.current_user_id')` 注入上下文
- **组织树穿透**：根组织的 owner/admin 可通过递归 CTE 访问所有子组织（Redis 缓存组织树 ID，TTL 1 小时）
- **家属跨组织访问**：`PatientFamilyLink` + RLS 策略允许家属查看关联患者的数据

### RBAC 权限体系

- **资源-操作解耦**：`rbac_resources` × `rbac_actions` → `permissions`（`resource:action` 编码格式）
- **递归角色继承**：通过 `parent_role_id` 实现层级式权限累积（递归 CTE 查询）
- **SSD 约束**：`RoleConstraint` 表实现静态责任分离
- **动态菜单**：`Permission.permission_type = "menu"` + `ui_metadata` JSONB 驱动前端导航
- **种子数据**：9 个资源、11 个操作、17 个权限点（10 API + 7 菜单）、4 个层级角色

### 认证体系

- JWT Token（PyJWT）+ OAuth2 Password Flow
- 密码重置：6 位数字验证码 + 15 分钟有效期（`PasswordResetToken` 表）
- API Key 认证：HMAC-SHA256 哈希存储 + 过期校验 + QPS 限流 + Token 配额
- 首位注册用户自动获得 `platform_admin` 角色

### 请求追踪与观测性

- `RequestIDMiddleware`：注入/透传 `X-Request-ID`，支持分布式追踪
- 全局异常捕获中间件，统一错误响应格式
- 增强版 `/health` 端点：检测 Redis + PostgreSQL 可达性
- assistant message metadata 中的 `observability` 字段记录每次 RAG 调用的详细指标

### 配额与限流

- 组织级 Token 配额：`Organization.quota_tokens_limit / quota_tokens_used`
- 流式配额检查：SSE 响应过程中实时检查并截断
- API Key 级别：QPS 限流 + Token 配额（`ApiKey.qps_limit / token_quota`）
- Redis 缓存优先，miss 时回退数据库

## 7. 本地开发

### 启动基础设施

```bash
docker compose up -d
```

服务列表：
- PostgreSQL (pgvector v0.5.1) — `localhost:5432`
- Redis 7 — `localhost:6379`
- MinIO — `localhost:9000`（控制台 `localhost:9001`）

### 安装依赖

```bash
cd backend
uv sync
```

### 初始化数据库

```bash
uv run alembic upgrade head
```

### 初始化 RBAC 种子数据

```bash
uv run python -m app.db.seed_rbac
```

### 启动服务

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 运行测试

```bash
uv run python -m pytest
```

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
| `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY` | — | Embedding 接口地址和密钥 |
| `RERANKER_PROVIDER` | `noop` | Reranker 供应商 |
| `RERANKER_MODEL` / `RERANKER_BASE_URL` / `RERANKER_API_KEY` | — | Reranker 配置 |

### RAG 参数

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RAG_VECTOR_WEIGHT` | `0.7` | 向量检索在 RRF 融合中的权重 |
| `RAG_KEYWORD_WEIGHT` | `0.3` | 关键词检索在 RRF 融合中的权重 |
| `RAG_RRF_K` | `60` | RRF 融合参数 k |
| `RAG_MIN_SCORE_THRESHOLD` | `0.0` | 检索结果最低分数阈值 |
| `RAG_CACHE_TTL` | `3600` | 检索缓存 TTL（秒） |
| `RAG_ENABLE_CONTEXTUAL_INGESTION` | `false` | 是否开启入库背景增强（消耗额外 Token） |

### 其他

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WORKER_ID` | — | 雪花算法节点 ID (0-1023) |
| `CORS_ORIGINS` | `localhost:3000,5173` | 允许的跨域来源 |
| `MAX_UPLOAD_SIZE_MB` | `50` | 最大上传文件大小 |
| `DEBUG_SQL` | `false` | 是否打印 SQL 日志 |

## 9. 当前剩余重点

- [ ] 接入真实可用的 Embedding Provider（当前推荐智谱 `embedding-3`）
- [ ] Reranker 从 `noop` 切换到实际 Provider
- [ ] 扩充离线评测样本并接入 CI
- [ ] 增加更细粒度的业务 filter（如按疾病类型、管理师过滤）
- [ ] 增强多轮对话压缩与专项评测
- [ ] 统一 LLM / Embedding / Reranker Provider 生命周期管理
- [ ] 密码重置邮件发送接入 SMTP（当前以日志代替）
- [ ] 审计日志异步化（当前同步写入，生产环境建议队列化）
- [ ] 健康指标异常告警逻辑
- [ ] 前端对接（B 端管理后台 + C 端患者/家属小程序）

## 10. 开发约定

- **ID 使用**：所有新表必须继承 `IDMixin`，默认生成 64 位雪花 ID。
- **类型提示**：ID 字段在 Python 中一律使用 `int` 类型。
- **接口返回**：直接返回 `int`，底层 `SnowflakeJSONResponse` 自动处理 JS 精度转换。
- **API 设计**：新增功能优先走 Provider / Service 抽象。
- **导入规范**：不要在导入阶段初始化外部服务（延迟初始化模式）。
- **权限控制**：管理类接口使用 `check_permission("resource:action")` 依赖注入。
- **组织隔离**：所有涉及租户数据的端点必须注入 `get_current_org` 并校验 `org_id`。
- **审计日志**：敏感操作（如家属查看患者数据）需调用 `audit_action()` 记录。
- **测试覆盖**：新功能需同时提交 API 测试和服务层单元测试。
