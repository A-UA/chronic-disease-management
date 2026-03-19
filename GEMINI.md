# Multi-Tenant AI SaaS 项目指南 (GEMINI.md)

本项目是一个高性能的多租户 AI SaaS 平台，核心业务围绕 RAG（检索增强生成）展开，并深度集成了 **B2B2C 医疗健康管理架构**，支持多组织管理、用量计费、API 接入及标准 RBAC 权限控制。

## 1. 项目概览

- **后端架构**：基于 **FastAPI** 异步框架，使用 **SQLAlchemy 2.0** 进行数据库操作，配合 **pgvector** 实现向量检索。
- **存储方案**：
  - **关系型/向量数据**：PostgreSQL (ankane/pgvector)。
  - **对象存储**：MinIO (S3 兼容)，用于原始文档存储。
  - **缓存/限流**：Redis (用于配额实时拦截、RAG 缓存、频率限制)。
- **核心特性**：
  - **多租户隔离**：通过 `org_id` 进行逻辑隔离，并在数据库层面使用 RLS (Row-Level Security) 确保数据安全，严防跨租户数据泄露。
  - **B2B2C 权限双轨制**：
    - **职能侧 (Staff)**：基于标准 RBAC (Role-Based Access Control)，通过原子权限（如 `patient:view`, `suggestion:create`）进行功能管控。
    - **用户侧 (Patient/Family)**：基于身份归属与 RLS 动态授权，严格隔离非本人/非授权数据。
  - **RAG 引擎**：结合 LangChain 处理文档分块、向量化及流式问答响应（SSE），内置 PII 敏感信息脱敏与 RAG 语义缓存。
  - **用量管控**：基于 Redis 实现 SSE 流式输出中的实时 Token 扣费与配额超限熔断。
  - **审计合规**：全量业务操作自动记录 AuditLog，支持多维度合规性溯源。

## 2. 目录结构说明

- `app/`: 后端核心代码。
  - `api/`: API 路由定义及依赖注入。
    - `endpoints/admin/`: 行政管理接口 (B端)，如机构设置、成员管控、知识库构建。
    - `endpoints/biz/`: 业务交互接口 (C端/管理师)，如患者画像、咨询聊天、管理建议。
    - `deps.py`: 核心依赖项（包含 RBAC 校验、RLS 注入、配额拦截）。
  - `core/`: 全局配置、安全性设置 (JWT, Argon2)。
  - `db/`: 数据库模型 (`models/`) 及异步会话管理。
    - `models/rbac.py`: 存储权限、角色、中间表等标准 RBAC 实体。
  - `services/`: 业务逻辑层（RAG 管道、用量统计、审计服务、存储等）。
- `alembic/`: 数据库迁移脚本。所有多租户表均强制启用 RLS。
- `docs/superpowers/`: 包含详细的设计规格 (`specs/`) 和实施方案 (`plans/`)。
- `tests/`: 涵盖 API 和服务的异步测试套件 (`pytest-asyncio`)。

## 3. 构建与运行指南

### 3.1 基础设施启动 (Docker)
项目依赖的外部服务可通过 Docker 快速启动：
```bash
docker compose up -d
```
这将启动 PostgreSQL (5432), Redis (6379) 和 MinIO (9000/9001)。

### 3.2 后端开发环境
1. **安装依赖** (使用 `uv` 管理包):
   ```bash
   uv sync
   ```
2. **数据库初始化** (迁移 + RBAC 种子数据):
   ```bash
   uv run alembic upgrade head
   uv run python app/db/seed_rbac.py
   ```
3. **启动应用**:
   ```bash
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   API 文档访问：`http://localhost:8000/docs`。

### 3.3 运行测试
执行完整的异步集成测试与单元测试：
```bash
uv run python -m pytest
```

## 4. 开发约定与最佳实践

- **多租户上下文与 RLS**：
  - 后端请求通常需要 `X-Organization-Id` 请求头。
  - 在 `app/api/deps.py` 中通过 `get_current_org_user` 解析上下文，并自动注入 `app.current_org_id` (RLS) 和 `app.current_user_id` (Cross-org Access)。
- **权限校验 (RBAC vs Identity)**：
  - **管理端操作**: 使用 `Depends(check_permission("perm_code"))`。
  - **患者端操作**: 使用 `Depends(require_patient_identity)`。
- **数据库操作**：
  - 始终使用异步 Session (`AsyncSession`)。
  - 高频过滤字段（如 `org_id` 与业务主键）必须通过 Alembic 手动添加复合索引以优化 RLS 扫描性能。
- **流式响应**：所有的流式响应（如 RAG 聊天）应使用 SSE (Server-Sent Events) 实现，且必须接入 `check_quota_during_stream` 实时拦截器。

## 5. TODO 与待办事项
- [x] 接入真实的标准 RBAC 权限体系。
- [x] 实现 API 命名空间物理拆分 (Admin vs Biz)。
- [ ] 实现针对家属和管理师的消息推送与提醒机制。
- [ ] 增加详细的各模型 Token 计费阶梯配置和计费中心看板。
- [ ] 完善组织邀请功能的邮件模板发送。
