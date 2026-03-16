# Multi-Tenant AI SaaS 项目指南 (GEMINI.md)

本项目是一个高性能的多租户 AI SaaS 平台，核心业务围绕 RAG（检索增强生成）展开，并深度集成了 **B2B2C 医疗健康管理架构**，支持多组织管理、用量计费、API 接入及 RBAC 权限控制。

## 1. 项目概览

- **后端架构**：基于 **FastAPI** 异步框架，使用 **SQLAlchemy 2.0** 进行数据库操作，配合 **pgvector** 实现向量检索。
- **存储方案**：
  - **关系型/向量数据**：PostgreSQL (ankane/pgvector)。
  - **对象存储**：MinIO (S3 兼容)，用于原始文档存储。
  - **缓存/限流**：Redis。
- **核心特性**：
  - **多租户隔离**：通过 `org_id` 进行逻辑隔离，并在数据库层面使用 RLS (Row-Level Security) 确保数据安全，严防跨租户数据泄露。
  - **B2B2C 医疗业务模型**：
    - **机构 (Organizations/B端)**：管理人员、分配患者、管控数据和资源（Token 用量）。
    - **管理师 (Managers/C端)**：作为专业服务人员，既可在后台，也可在移动端（应用层）查看分配给自己的患者并撰写管理建议。受 RBAC 与 RLS 双重管控。
    - **患者 (Patients/C端)**：拥有专属医疗档案，数据强绑定在服务机构（B端）内。
    - **家属 (Family/C端)**：跨机构动态授权。家属无需属于某机构即可通过 `patient_family_links` 获权查看患者数据。
  - **RAG 引擎**：结合 LangChain 处理文档分块、向量化及流式问答响应（SSE）。
  - **用量管控**：精细化记录 Token 消耗，支持组织级配额限制和 API 密钥 QPS 限流（Redis 异步）。
  - **权限体系 (RBAC)**：支持超级管理员 (Owner/Admin) 全局管理视图与普通成员 (Member/管理师) 的受限业务视图。

## 2. 目录结构说明

- `app/`: 后端核心代码。
  - `api/`: API 路由定义及依赖注入 (`deps.py` 包含租户上下文解析与 RLS 注入)。
    - `endpoints/`: 包含 `auth`, `organizations` (行政), `managers` (业务), `patients`, `family` 等模块化 API。
  - `core/`: 全局配置、安全性设置 (JWT, Argon2)。
  - `db/`: 数据库模型 (`models/`) 及异步会话管理 (`session.py`)。
  - `services/`: 业务逻辑层（RAG 管道、用量统计、存储等）。
- `alembic/`: 数据库迁移脚本。所有多租户表的迁移中均硬编码启用了 RLS。
- `docs/superpowers/`: 包含详细的设计规格 (`specs/`) 和实施方案 (`plans/`)。
- `tests/`: 涵盖 API 和服务的自动化测试套件 (`pytest-asyncio`)。

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
2. **运行数据库迁移** (包含新表的 RLS 策略):
   ```bash
   uv run alembic upgrade head
   ```
3. **启动应用**:
   ```bash
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   API 文档访问：`http://localhost:8000/docs` 或 `/api/v1/docs`。

### 3.3 运行测试
执行完整的异步集成测试与单元测试：
```bash
uv run python -m pytest
```

## 4. 开发约定与最佳实践

- **多租户上下文与 RLS**：
  - 后端请求通常需要 `X-Organization-Id` 请求头来指定当前组织环境。
  - 在 `app/api/deps.py` 中通过 `get_current_org` 获取，并通过 `SELECT set_config('app.current_org_id', :org_id, true)` 注入 PostgreSQL RLS 上下文。
- **业务域与行政域解耦 (API 设计)**：
  - **行政管理 (B端)**: 归属于 `organizations.py`，如 `POST /organizations/{org_id}/assignments`，必须校验 Admin 角色。
  - **业务执行 (C端/双栖)**: 归属于 `managers.py`、`patients.py` 等，注重实际业务交互，通过 RBAC 决定数据可见范围。
- **数据库操作**：
  - 始终使用异步 Session (`AsyncSession`)。
  - 新增需隔离的数据模型必须继承自 `app.db.models.base.Base` 并包含 `org_id` 字段。在 Alembic 迁移时必须手动注入 `ENABLE ROW LEVEL SECURITY`。
- **流式响应**：所有的流式响应（如 RAG 聊天）应使用 SSE (Server-Sent Events) 实现。

## 5. TODO 与待办事项
- [ ] 接入真实的 OpenAI/LangChain Embedding 以替换目前的 Mock 向量检索。
- [ ] 实现针对家属和管理师的消息推送与提醒机制。
- [ ] 增加详细的各模型 Token 计费阶梯配置和计费中心看板。
- [ ] 完善组织邀请功能的邮件模板发送。
