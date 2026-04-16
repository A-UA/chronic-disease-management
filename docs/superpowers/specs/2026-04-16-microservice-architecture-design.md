# 慢病管理微服务架构拆分设计文档

> 创建日期：2026-04-16
> 状态：已确认

## 1. 背景与动机

将当前 Python (FastAPI) 全栈后端拆分为多语言微服务架构，**核心目的是学习与对比**：

- 用同一套业务逻辑，分别用 **Java Spring Boot** 和 **NestJS** 各实现一遍
- Python 精简为纯 **AI 中间层 (Agent)**，只负责 LLM/RAG/Agent 相关计算
- 横向对比两个框架在鉴权、ORM、多租户、RBAC 等核心领域的写法差异

## 2. 整体架构

### 2.1 系统拓扑

```
前端 (React, 5173)
  │
  ├── VITE_BACKEND=java ──→ [Java API Gateway] (8000)
  │                              ├──→ [auth-service]    (8010)  HTTP
  │                              ├──→ [patient-service] (8020)  HTTP
  │                              └──→ [chat-service]    (8030)  HTTP
  │                                       │
  │                                       ▼
  │                              [Python Agent] (8100)  ← 内部 HTTP
  │
  └── VITE_BACKEND=nestjs ─→ [NestJS API Gateway] (8001)
                                 ├──→ [auth-service]    (8011)  TCP
                                 ├──→ [patient-service] (8021)  TCP
                                 └──→ [chat-service]    (8031)  TCP
                                          │
                                          ▼
                                 [Python Agent] (8100)  ← 内部 HTTP
```

### 2.2 核心原则

- **Python Agent 不碰业务数据库**：Agent 只与 Milvus（向量数据库）和 LLM 接口交互
- **Agent 完全重构**：原 `backend/` 中的业务模块（路由、服务、仓储、ORM 模型等）全部删除，从零构建纯 AI 中间层服务
- **镜像实现**：Java 和 NestJS 各自完整实现相同的业务模块，便于对比
- **共享数据库**：Java 和 NestJS 连同一个 PostgreSQL，DDL 迁移由 Alembic 统一管理
- **前端无侵入切换**：通过环境变量切换代理目标端口

## 3. 仓库目录结构

```
chronic-disease-management/
├── agent/                        # Python AI 中间层（原 backend/ 完全重构）
│   ├── app/
│   │   ├── main.py               # FastAPI 入口（仅内部接口）
│   │   ├── config.py             # 配置（Milvus、LLM、Redis 等）
│   │   ├── rag/                  # RAG 检索引擎（扁平化，无 ai/ 嵌套）
│   │   │   ├── retrieval.py      # 向量检索（对接 Milvus）
│   │   │   ├── ingestion.py      # 文档切块 + Embedding + 写入 Milvus
│   │   │   ├── citation.py       # 引用构建
│   │   │   ├── context.py        # 上下文增强
│   │   │   └── compress.py       # 对话历史压缩
│   │   ├── graph/                # LangGraph Agent（原 ai/agent/，重命名避免冲突）
│   │   │   ├── graph.py          # 图定义与执行
│   │   │   ├── state.py          # 状态定义
│   │   │   └── skills/           # 工具技能
│   │   ├── plugins/              # 插件体系（LLM/Embedding/Reranker/Parser/Chunker）
│   │   │   └── registry.py
│   │   ├── vectorstore/          # 向量数据库客户端
│   │   │   ├── base.py           # Protocol 抽象
│   │   │   └── milvus.py         # Milvus 实现
│   │   ├── schemas/              # 内部接口请求/响应模型
│   │   └── tasks/                # arq 异步任务（文档入库）
│   │       └── worker.py
│   └── pyproject.toml
│
├── backend-java/                 # Java Spring Boot 微服务集群
│   ├── gateway/                  # API 网关（Spring Cloud Gateway）
│   ├── auth-service/             # 认证/用户/组织/RBAC 微服务
│   ├── patient-service/          # 患者/健康指标微服务
│   ├── chat-service/             # 对话管理微服务
│   ├── common-lib/               # 共享库
│   └── pom.xml                   # 父 POM
│
├── backend-nestjs/               # NestJS 微服务集群
│   ├── gateway/                  # API 网关（Nest HTTP 应用）
│   ├── auth-service/             # 认证/用户/组织/RBAC 微服务（TCP）
│   ├── patient-service/          # 患者/健康指标微服务（TCP）
│   ├── chat-service/             # 对话管理微服务（TCP）
│   ├── shared/                   # 共享库
│   ├── package.json
│   └── tsconfig.base.json
│
├── database/                     # 共享数据库管理
│   ├── alembic/                  # DDL 迁移脚本（Alembic）
│   ├── alembic.ini
│   └── seed.py                   # 种子数据（RBAC + 菜单 + 超管）
│
├── frontend/                     # React 前端（不变）
├── docker-compose.yml
└── AGENTS.md
```

## 4. 数据存储职责分离

| 存储 | 管理方 | 用途 |
|------|--------|------|
| **PostgreSQL 16** (标准版，无 pgvector) | Java / NestJS | 所有业务数据（用户、组织、患者、文档元数据、对话记录、RBAC 等） |
| **Milvus** | Python Agent | 向量索引 + 切块元数据（payload 字段承载） |
| **Redis** | 共享 | 缓存、限流 |
| **MinIO** | 共享 | 文件对象存储 |

### 4.1 chunk 表迁移

- 原 PostgreSQL 中的 `chunk` 表**完全移除**
- `chunk` 的 `embedding` 向量列 → Milvus 的向量字段
- `chunk` 的元数据（`document_id`、`chunk_index`、`content`、`token_count` 等）→ Milvus 的 payload/scalar 字段
- `document` 表保留在 PostgreSQL 中，由业务后端管理 CRUD

### 4.2 Agent 重构策略（完全重建）

原 `backend/` 重命名为 `agent/` 后，以下模块**全部删除**，不做保留或迁移：

| 删除的模块 | 原路径 | 原因 |
|-----------|--------|------|
| 路由层 | `routers/` | 所有 HTTP 端点由 Java/NestJS 实现 |
| 服务层 | `services/` | 业务编排由 Java/NestJS 实现 |
| 仓储层 | `repositories/` | 数据库访问由 Java/NestJS 实现 |
| ORM 模型 | `models/` | 实体定义由 Java/NestJS 实现 |
| 请求响应模型 | `schemas/` | 重建为仅包含 Agent 内部接口的模型 |
| 基础设施 | `base/` | 重建为仅包含 Agent 自身配置（无 JWT、无数据库连接） |
| 种子数据 | `seed.py` | 迁移至 `database/seed.py` |
| 数据库迁移 | `alembic/` | 迁移至 `database/alembic/` |
| 可观测性 | `telemetry/` | 按需在 Agent 中从零引入轻量方案 |

**保留并重构的模块**：

| 保留的模块 | 原路径 → 新路径 | 重构说明 |
|-----------|----------------|----------|
| RAG 引擎 | `ai/rag/` → `rag/` | 提升一级，消除 `ai/` 嵌套；重构数据层对接 Milvus |
| Agent 图执行 | `ai/agent/` → `graph/` | 重命名避免与项目名冲突；保留 LangGraph 图执行逻辑 |
| 插件体系 | `plugins/` → `plugins/` | 保留 LLM/Embedding/Reranker/Parser/Chunker |
| 异步任务 | `tasks/` → `tasks/` | 保留 arq Worker，任务内容简化为纯 AI 任务 |

## 5. Python Agent 内部 API 契约

所有接口仅限内网访问，无需鉴权。基础路径：`http://agent:8100`

### 5.1 接口清单

| 方法 | 路径 | 用途 | 返回 |
|------|------|------|------|
| `POST` | `/internal/ingest` | 文档切块 + Embedding + 写入 Milvus | 切块数量、状态 |
| `DELETE` | `/internal/chunks` | 按文档 ID 删除 Milvus 中的切块 | 删除数量 |
| `POST` | `/internal/chat` | RAG 检索 + LLM 对话（SSE 流式） | SSE 事件流 |
| `POST` | `/internal/chat/sync` | RAG 检索 + LLM 对话（同步） | JSON 完整回复 |
| `POST` | `/internal/compress` | 对话历史压缩摘要 | 压缩后文本 |
| `GET` | `/internal/health` | 健康检查 | `{"status": "ok"}` |

### 5.2 文档入库 `/internal/ingest`

```jsonc
// 请求
{
  "document_id": 123456,
  "kb_id": 789,
  "file_url": "minio://docs/xx.pdf",
  "file_name": "糖尿病指南.pdf",
  "tenant_id": 1
}

// 响应
{
  "status": "completed",
  "chunk_count": 42,
  "token_count": 8500
}
```

### 5.3 RAG 对话 `/internal/chat` (SSE)

```jsonc
// 请求
{
  "query": "糖尿病患者的饮食注意事项有哪些？",
  "kb_ids": [789, 790],
  "history": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好，有什么可以帮您？"}
  ],
  "tenant_id": 1,
  "config": {
    "top_k": 5,
    "temperature": 0.7
  }
}

// SSE 响应事件流
event: chunk
data: {"content": "糖尿病患者"}

event: chunk
data: {"content": "应注意以下"}

event: citations
data: {"citations": [{"doc_id": 123, "chunk_text": "...", "score": 0.92}]}

event: usage
data: {"prompt_tokens": 1200, "completion_tokens": 350}

event: done
data: {}
```

### 5.4 删除切块 `/internal/chunks`

```jsonc
// 请求
{ "document_id": 123456, "kb_id": 789 }

// 响应
{ "deleted_count": 42 }
```

### 5.5 调用流程示例（RAG 对话）

```
前端 → Java/NestJS:  POST /api/v1/chat  (携带 JWT)
         │
         ├─ 1. 网关鉴权、注入身份上下文
         ├─ 2. chat-service：从 PostgreSQL 查出对话历史、知识库配置
         ├─ 3. 组装上下文，调用 Agent：POST http://agent:8100/internal/chat
         │
Agent ←──┘
         ├─ 4. 用 kb_ids 去 Milvus 检索相关切块
         ├─ 5. 构建 Prompt + 调用 LLM（SSE 流式）
         └─ 6. 返回流式响应 + 引用信息
                  │
Java/NestJS ←────┘
         ├─ 7. 将 AI 回复写入 PostgreSQL（对话/消息表）
         └─ 8. SSE 流式透传给前端
```

## 6. Java Spring Boot 微服务架构

### 6.1 拓扑

```
[Java API Gateway] (8000)  ← Spring Cloud Gateway
  ├──→ [auth-service]    (8010)
  ├──→ [patient-service] (8020)
  └──→ [chat-service]    (8030) ──→ [Agent] (8100)
```

### 6.2 技术栈

| 层级 | 选型 |
|------|------|
| 框架 | Spring Boot 3.x (Java 17+) |
| 网关 | Spring Cloud Gateway |
| 安全 | Sa-Token (JWT Stateless) |
| ORM | Spring Data JPA + Hibernate |
| 构建 | Maven, 多模块 |
| HTTP 客户端 | WebClient (WebFlux) |
| 校验 | Jakarta Validation |
| 文档 | SpringDoc OpenAPI |

### 6.3 模块结构

每个微服务按职责分层（标准 Spring Boot 微服务分包）：

```
auth-service/src/main/java/com/cdm/auth/
├── AuthServiceApplication.java
├── config/                     # 配置层
│   └── SaTokenConfig.java
├── controller/                 # 控制器层（HTTP 适配）
│   └── AuthController.java
├── service/                    # 服务层（业务编排）
│   ├── AuthService.java
│   └── MenuService.java
├── repository/                 # 数据访问层
│   ├── UserRepository.java
│   ├── OrganizationRepository.java
│   └── ...
├── entity/                     # 实体层（ORM 映射）
│   ├── BaseEntity.java
│   ├── UserEntity.java
│   └── ...
├── dto/                        # 数据传输对象
│   ├── LoginRequest.java
│   └── ...
├── security/                   # 安全/权限
│   ├── StpInterfaceImpl.java
│   └── IdentityContext.java
├── util/                       # 工具类
│   └── SnowflakeIdGenerator.java
└── exception/                  # 异常处理
    ├── BusinessException.java
    └── GlobalExceptionHandler.java
```

### 6.4 网关路由配置

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: auth-service
          uri: http://localhost:8010
          predicates:
            - Path=/api/v1/auth/**, /api/v1/users/**, /api/v1/organizations/**, /api/v1/rbac/**
        - id: patient-service
          uri: http://localhost:8020
          predicates:
            - Path=/api/v1/patients/**, /api/v1/health-metrics/**
        - id: chat-service
          uri: http://localhost:8030
          predicates:
            - Path=/api/v1/chat/**, /api/v1/conversations/**
```

### 6.5 网关鉴权流程

```
请求进入 Gateway (8000)
  │
  ▼
JwtAuthFilter（全局过滤器）
  ├─ 白名单路径？（/auth/login, /auth/register）→ 直接放行
  ├─ 解析 JWT → 失败 → 返回 401
  └─ 成功 → 注入安全 Header：
       X-User-Id / X-Tenant-Id / X-Org-Id / X-Roles
         │
         ▼
    路由转发到目标微服务
         │
         ▼
    微服务直接从 Header 读取身份信息（信任网关）
```

## 7. NestJS 微服务架构

### 7.1 拓扑

```
[NestJS API Gateway] (8001)  ← 标准 Nest HTTP 应用
  ├──→ [auth-service]    (8011)  TCP
  ├──→ [patient-service] (8021)  TCP
  └──→ [chat-service]    (8031)  TCP ──→ [Agent] (8100)
```

### 7.2 技术栈

| 层级 | 选型 |
|------|------|
| 框架 | NestJS 10.x |
| 微服务 | @nestjs/microservices (TCP 传输层) |
| 安全 | Passport + JWT (@nestjs/jwt) |
| ORM | TypeORM |
| 包管理 | pnpm workspace (monorepo) |
| HTTP 客户端 | @nestjs/axios (HttpService) |
| 校验 | class-validator + class-transformer |
| 文档 | @nestjs/swagger |

### 7.3 模块结构

每个微服务按业务领域聚合：

```
auth-service/src/
├── main.ts                         # createMicroservice(Transport.TCP, 8011)
├── app.module.ts
├── auth/
│   ├── auth.controller.ts          # @MessagePattern({ cmd: 'login' })
│   ├── auth.service.ts
│   └── dto/
├── user/
│   ├── user.controller.ts          # @MessagePattern({ cmd: 'list_users' })
│   ├── user.service.ts
│   ├── user.repository.ts
│   ├── user.entity.ts
│   └── dto/
├── organization/
│   ├── org.controller.ts
│   ├── org.service.ts
│   ├── org.repository.ts
│   ├── org.entity.ts
│   └── dto/
├── rbac/
│   ├── rbac.controller.ts
│   ├── rbac.service.ts
│   ├── role.entity.ts
│   └── permission.entity.ts
└── common/
    ├── base.entity.ts
    └── rpc-exception.filter.ts
```

### 7.4 网关代理模式

```typescript
// 网关 Controller：接 HTTP → 打包 → send 给 TCP 微服务
@Controller('api/v1/patients')
@UseGuards(JwtAuthGuard)
export class PatientProxyController {
  constructor(@Inject('PATIENT_SERVICE') private client: ClientProxy) {}

  @Post()
  @RequirePermission('patient:create')
  async create(@CurrentUser() user, @Body() dto) {
    return firstValueFrom(
      this.client.send({ cmd: 'create_patient' }, { user, data: dto }),
    );
  }
}
```

### 7.5 Java vs NestJS 关键差异

| 维度 | Java Spring Cloud | NestJS |
|------|-------------------|--------|
| 网关类型 | 声明式（YAML 路由 + Filter 链） | 编程式（Controller + ClientProxy） |
| 内部通信 | HTTP（服务间 REST 调用） | TCP（NestJS 原生微服务协议） |
| 鉴权传递 | Sa-Token SaReactorFilter + Header 透传 | JWT Guard + Payload 对象直接传递 |
| ORM | JPA / Hibernate | TypeORM |
| 共享库 | Maven 子模块 | npm 包 (pnpm workspace) |
| 异常体系 | @ControllerAdvice | RpcExceptionFilter |

## 8. 基础设施

### 8.1 端口分配

| 服务 | 端口 | 用途 |
|------|------|------|
| PostgreSQL 16 | 5432 | 共享业务数据库（标准版，无 pgvector） |
| Redis 7 | 6379 | 缓存/限流 |
| MinIO | 9000/9001 | 对象存储 |
| Milvus | 19530 | 向量数据库（Agent 专属） |
| Python Agent | 8100 | AI 内部服务 |
| Java Gateway | 8000 | Java 微服务网关 |
| Java auth-service | 8010 | 内部 HTTP |
| Java patient-service | 8020 | 内部 HTTP |
| Java chat-service | 8030 | 内部 HTTP |
| NestJS Gateway | 8001 | NestJS 微服务网关 |
| NestJS auth-service | 8011 | 内部 TCP |
| NestJS patient-service | 8021 | 内部 TCP |
| NestJS chat-service | 8031 | 内部 TCP |
| 前端 | 5173 | Vite 开发服务器 |

### 8.2 前端切换

```typescript
// vite.config.ts
const backendPort = {
  java: 8000,
  nestjs: 8001,
}[process.env.VITE_BACKEND || 'java'];

server: {
  proxy: { '/api': { target: `http://localhost:${backendPort}` } }
}
```

### 8.3 密码哈希兼容

- 原 Argon2、Java BCrypt、NestJS bcrypt 互不兼容
- 密码字段根据前缀（`$argon2id$`、`$2a$`）自动选择验证算法
- 各后端的 seed 脚本用各自算法重新生成超管密码

## 9. 分期实施计划

### 第一期：基础骨架（跑通端到端登录链路）

| 编号 | 任务 | 说明 |
|------|------|------|
| P1-1 | 重命名 `backend/` → `agent/`，完全重构 | 删除所有业务模块（routers/services/repositories/models/schemas/base），仅保留 ai/ + plugins/ + tasks/，从零构建纯 AI 服务 |
| P1-2 | Agent 接入 Milvus | 替换 pgvector，移除 chunk 表 |
| P1-3 | Agent 暴露 `/internal/*` 接口 | 按契约实现 6 个内部端点 |
| P1-4 | Java: gateway + auth-service | 登录/JWT/me/菜单树 |
| P1-5 | NestJS: gateway + auth-service | 登录/JWT/me/菜单树 |
| P1-6 | 前端切换机制 | 环境变量控制代理端口 |

**里程碑**：前端能通过 Java 或 NestJS 完成登录。

### 第二期：核心业务（CRUD + 权限）

| 编号 | 任务 |
|------|------|
| P2-1 | Java/NestJS: 用户管理 + 组织管理 |
| P2-2 | Java/NestJS: RBAC 权限体系 + RLS |
| P2-3 | Java/NestJS: 患者 CRUD + 健康指标 |

**里程碑**：前端核心页面全部可用。

### 第三期：AI 对话链路

| 编号 | 任务 |
|------|------|
| P3-1 | Java/NestJS: chat-service + Agent 客户端 |
| P3-2 | SSE 流式透传完整链路 |
| P3-3 | 文档上传 → Agent 入库 → Milvus |

**里程碑**：RAG 对话端到端可用。

### 第四期：完善与对比

| 编号 | 任务 |
|------|------|
| P4-1 | 审计日志、仪表盘、配额等辅助模块 |
| P4-2 | 两个后端的性能对比测试 |
| P4-3 | 撰写学习对比报告 |

## 10. 首期模块范围（Python 对照表）

| Python 原版模块 | Java 对应 | NestJS 对应 |
|----------------|-----------|-------------|
| `routers/auth/` | `auth-service/auth/` | `auth-service/auth/` |
| `routers/system/users.py` | `auth-service/user/` | `auth-service/user/` |
| `routers/system/organizations.py` | `auth-service/organization/` | `auth-service/organization/` |
| `routers/system/rbac.py` | `auth-service/rbac/` | `auth-service/rbac/` |
| `routers/patient/patients.py` | `patient-service/patient/` | `patient-service/patient/` |
| `routers/patient/health_metrics.py` | `patient-service/metric/` | `patient-service/metric/` |
| `routers/rag/chat_runtime.py` | `chat-service/conversation/` + `agent/` | `chat-service/conversation/` + `agent/` |
| `routers/deps.py` (JWT) | `gateway/filter/JwtAuthFilter` | `gateway/guards/jwt-auth.guard` |
| `routers/deps.py` (RLS) | `gateway/filter/RlsContextFilter` | `gateway/guards/` or `interceptor` |
| `routers/deps.py` (RBAC) | `common-lib/PermissionChecker` (AOP) | `shared/permission.guard` |
