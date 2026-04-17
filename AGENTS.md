# 慢病管理多租户 AI SaaS — 项目指南

更新时间：2026-04-18

## 1. 项目概览

面向慢病管理场景的多租户 AI SaaS 全栈项目。本项目近期经历了架构大重构，将原有的 Python 单体应用升级为**多语言微服务架构 (Polyglot Microservices)**，包含一套独立的 **Python AI Agent 中间件**，以及由 **Java/NestJS 提供双平台参考实现**的核心业务微服务，配合原有的 React 前端管理后台。

核心能力：
- **微服务/网关设计**：通过统一 Gateway 路由请求，下层拆分为 Auth Service（用户/组织/RBAC）与 Patient Service（慢病健康档案/指标/家属/知识库）。
- **Python Agent 中间件**：独立的 AI 原生服务，基于 LangGraph 构建带有工具回调、记忆增强和动态技能加载能力的大模型编排引擎。
- **RAG 与存储解耦**：从 PostgreSQL 完整解理为直连 Milvus 向量数据库，并依托于 LangChain 工具链进行召回上下文组合。
- **管理后台**：React 19 + Tailwind CSS V4 体系下提供的动态菜单路由、数据看板、多租户 RBAC、流式对话气泡的现代前端。

## 2. 系统核心架构与技术栈

### 2.1 核心业务微服务双实现（后端）
为了适应多团队技术栈演进，核心业务服务提供两套等价架构（实际部署时只保留其一或按域切分）：

#### 方案 A: Java + Spring Cloud
- **技术栈**: Java, Spring Boot 3.x, Spring Cloud Gateway, Sa-Token（全局鉴权拦截）, MyBatis-Plus / Spring Data JPA。
- **结构**: Maven 多模块结构 (`gateway` / `auth-service` / `patient-service` / `common-lib`)。
- **服务通信**: 基于 Spring Cloud 内部调用规范。

#### 方案 B: Node.js + NestJS
- **技术栈**: TypeScript (strict, 零 `any`), NestJS 11.x, TypeORM 0.3.x, Node ≥20.19。
- **结构**: PNPM 10 Workspace + Turborepo Monorepo (`apps/gateway` / `apps/auth` / `apps/patient` / `libs/shared`)。
- **类型体系**: 严格的 DTO/VO 分层，入站参数使用 DTO（`libs/shared/src/dto/`），出站响应使用 VO（`libs/shared/src/vo/`）。所有 Service 方法通过 `static toVO()` 工厂方法做 Entity→VO 转换，禁止直接透传 Entity（防止 `passwordHash` 等敏感字段泄漏）。
- **服务通信**: 微服务间使用 `@nestjs/microservices` 原生 TCP 传输与消息代理通信模式，提升内网调用效率。
- **API 文档**: Gateway 集成 `@nestjs/swagger` 11.x，自动生成 OpenAPI 文档，访问路径 `/api/docs`。
- **输入校验**: Gateway HTTP 层启用 `class-validator` + `ValidationPipe({ transform: true, whitelist: true })` 全局管道。

### 2.2 Agent 中间件 (Python)
完全取代了原有单体服务的 AI 管线。
- **工作流框架**: LangGraph (`StateGraph`), 基于 `@tool` 节点调度的循环控制。
- **网络服务**: FastAPI, SSE (`sse-starlette`) 实现事件级流式输出 (`astream_events`)。
- **环境打包工具**: `uv` 作为现代化构建和包管理器。
- **大模型 / RAG**: `langchain-openai`, `langchain-milvus`，结合直连 `Milvus` 进行高维向量检索。
- **动态技能组件**: 利用 `agentskills.io` 思想开发的 `markdown_loader` 从 `skills/` 下的 `.md` 中注入外接指令。

### 2.3 前端 (React monorepo)
- **技术栈**: React 19, TypeScript 5.x, Vite 8 工具链 (`vp`), Zustand。
- **样式**: Tailwind CSS 4.x（`@tailwindcss/vite` 插件接入，重构为直接在 CSS 中注入 `@theme` Design Token）。
- **组件库**: Ant Design 6.x（兼容性改造避免 preflight 覆盖）。

## 3. 全局目录结构

```
chronic-disease-management/
├── backend-java/                  # Java 业务微服务群
│   ├── common-lib/                # 通用 DTO / 过滤器 / 异常类
│   ├── gateway/                   # Spring Gateway + SaToken
│   ├── auth-service/              # RBAC 角色、租户、JWT 鉴权服务
│   ├── patient-service/           # 患者档案、家属、健康指标相关服务
│   └── pom.xml                    # Maven 聚合构建配置
├── backend-nestjs/                # Nest.js 业务微服务群 (Turborepo Monorepo)
│   ├── libs/shared/               # 共享库
│   │   ├── src/constants.ts       # 服务标识、TCP 命令常量
│   │   ├── src/interfaces/        # IdentityPayload 等核心接口
│   │   ├── src/dto/               # 入站 DTO (crud-payload, auth, patient, gateway 等)
│   │   ├── src/vo/                # 出站 VO (auth.vo, patient.vo)
│   │   ├── src/utils/             # snowflake ID 生成器
│   │   ├── src/config/            # 数据库连接配置 (database.config.ts)
│   │   └── src/interceptors/      # BigInt 序列化拦截器
│   ├── apps/gateway/              # HTTP 网关 (端口 8001)
│   │   ├── src/guards/            # JwtAuthGuard (JWT 验证 + RequestWithIdentity)
│   │   ├── src/decorators/        # @CurrentUser 参数装饰器
│   │   ├── src/filters/           # RpcExceptionToHttpFilter (微服务异常转 HTTP)
│   │   └── src/proxy/             # 15 个 Proxy Controller + AgentProxyService + MinioProxyService
│   ├── apps/auth/                 # Auth 微服务 (TCP 端口 8011)
│   │   ├── src/auth/              # 登录/选择组织/切换组织/JWT 签发
│   │   ├── src/user/              # 用户 CRUD
│   │   ├── src/organization/      # 租户 + 组织 + 组织-用户关联 + 组织-用户-角色关联
│   │   ├── src/rbac/              # 角色 + 权限 CRUD
│   │   └── src/menu/              # 菜单 CRUD + 树形构建
│   ├── apps/patient/              # Patient 微服务 (TCP 端口 8021)
│   │   ├── src/patient/           # 患者档案 CRUD
│   │   ├── src/health-metric/     # 健康指标记录
│   │   ├── src/management-suggestion/ # 管理建议
│   │   ├── src/manager-assignment/    # 管理人分配
│   │   ├── src/patient-family-link/   # 家属关联
│   │   └── src/knowledge/         # 知识库 + 文档管理 (entities/ 子目录)
│   ├── pnpm-workspace.yaml        # PNPM + Catalog 依赖版本锁定
│   ├── turbo.json                 # Turborepo 任务编排配置
│   ├── tsconfig.base.json         # 全局 TS 配置 (strict + noImplicitAny)
│   └── package.json               # 工作区脚本 (dev/build/lint/test)
├── agent/                         # AI Agent 运行时环境
│   ├── app/                       
│   │   ├── config.py              # Pydantic 环境变量绑定
│   │   ├── main.py                # FastAPI 初始化
│   │   ├── routers/               
│   │   │   └── internal.py        # Gateway 专用的 SSE 通信口 /chat 
│   │   └── agent/
│   │       ├── graph.py           # LangGraph StateGraph 装配器
│   │       └── tools/             
│   │           ├── markdown_loader.py # 动态 `SKILL.md` 指令装载器
│   │           └── rag_tool.py    # Milvus 向量知识库查询模块
│   ├── tests/                     # 基于 pytest 的独立测试
│   ├── skills/                    # 专供 Agent 解析的第三方技能目录
│   └── pyproject.toml             # uv 项目依赖配置
├── frontend/                      # React 管理后台
│   ├── apps/website/src/          
│   └── vite.config.ts             
├── database/                      # 数据库 SQL 脚本 (PostgreSQL)
│   └── init.sql                   # 建表 + 索引 + 种子数据（手动执行）
└── AGENTS.md                      # 本说明文档
```

## 4. 服务通信与数据流

### 4.1 端口分配

| 服务 | 协议 | 端口 | 说明 |
|------|------|------|------|
| Gateway | HTTP | 8001 | 统一 API 入口 (Swagger: `/api/docs`) |
| Auth Service | TCP | 8011 | 用户/组织/RBAC 微服务 |
| Patient Service | TCP | 8021 | 患者/健康/知识库微服务 |
| Agent | HTTP | 8000 | AI Agent SSE 流式接口 |

### 4.2 请求链路

整体外部请求链路向微服务网关 (Gateway) 收拢，各子服务分工明确：

1. **客户端请求** → 触达 `Gateway` (`:8001/api/v1/...`)。
2. **鉴权**：
   - `JwtAuthGuard` 拦截所有需鉴权请求，验证 JWT 后将身份信息注入 `RequestWithIdentity.identity`（类型为 `IdentityPayload`）。
   - `@CurrentUser()` 装饰器在 Controller 中提取身份上下文。
3. **流量分发**（Gateway 通过 `ClientProxy.send()` TCP 转发至下游微服务）：
   - `/api/v1/auth/**` · `/api/v1/users/**` · `/api/v1/tenants/**` · `/api/v1/organizations/**` · `/api/v1/roles/**` · `/api/v1/permissions/**` · `/api/v1/menus/**` → `auth-service`
   - `/api/v1/patients/**` · `/api/v1/health-metrics/**` · `/api/v1/management-suggestions/**` · `/api/v1/manager-assignments/**` · `/api/v1/patient-family-links/**` · `/api/v1/knowledge-bases/**` · `/api/v1/documents/**` → `patient-service`
   - `/api/v1/chat` · `/api/v1/conversations/**` → Gateway 内 `AgentProxyService` 直连 Agent HTTP 接口，SSE 流式透传
4. **文件上传流** (知识库文档)：
   - 客户端 `POST /api/v1/documents/kb/:kbId/documents` multipart 上传
   - Gateway `MinioProxyService` 将文件上传至 MinIO 对象存储
   - Gateway `AgentProxyService.parseDocument()` 调用 Agent 解析文档为向量切片
   - Gateway 将元数据通过 TCP 同步至 `patient-service` 持久化
5. **Agent 执行**：
   - Agent 收到 `ChatRequest`（包裹 `query`、`history` 和 `metadata.kb_id`配置）。
   - LangGraph 被激活，ChatOpenAI 基于上下文判断调用。
   - 若命中 `rag_search_handler`，Agent 跳入 ToolNode 并从 `RunnableConfig` 中获取知识库 ID 限制作用域，直连检索 Milvus。
   - `internal.py` 的流式接口根据解析 `astream_events` 实时推送文字块 (`message`) 和工具调用记录/引用元数据 (`tool_start`/`tool_end`) 返回至 Gateway。

## 5. 本地开发指南

由于项目转变为微服务架构，可以根据您维护的系统选取不同终端执行：

### 5.1 启动基础设施
```bash
docker-compose up -d
# 服务：PostgreSQL (关系业务与鉴权数据库), Redis, Milvus (向量存储), MinIO (对象存储)
```

### 5.2 初始化数据库
DDL 由 `database/init.sql` 手动管理，后端服务均禁用了自动建表。首次部署或重建数据库时执行：
```powershell
psql -h localhost -U postgres -d <数据库名> -f database/init.sql
```

### 5.3 启动 Agent (Python 3.12)
推荐使用官方 `uv` 运行。
```powershell
cd agent
uv sync
$env:OPENAI_API_KEY="sk-xxx" 
$env:MILVUS_HOST="localhost"
uv run uvicorn app.main:app --reload --port 8000
```
> 测试运行：`uv run pytest`

### 5.4 启动后端业务服务
- **Java**：使用 Maven 或 IDEA 打开 `backend-java` 并按序启动 Gateway、Auth 服务。（`ddl-auto: none`，必须先执行 5.2）
- **NestJS**：在 `backend-nestjs` 运行 `pnpm install` 安装所有依赖并执行 `pnpm run build`。平时开发可使用以下脚本单独启动服务，或直接 `pnpm dev` 通过 Turborepo 全量启动。（`synchronize: false`，必须先执行 5.2；TCP 微服务需先于网关启动）

```powershell
# 全量启动（推荐，Turbo 自动编排依赖顺序）
pnpm dev

# 单独启动某个微服务
pnpm dev:gateway   # HTTP Gateway :8001
pnpm dev:auth      # Auth TCP :8011
pnpm dev:patient   # Patient TCP :8021
```

### 5.5 启动前端后台
```powershell
cd frontend
vp install 
vp dev
```

## 6. 代码提交检查标准

* **数据库变更**：任何表结构修改必须同步更新 `database/init.sql`，禁止依赖 ORM 自动同步。NestJS `synchronize` 和 Java `ddl-auto` 均已锁定为关闭状态。
* **TypeScript 类型纪律（NestJS）**：
  - **禁止 `any`**：不允许 `: any`、`as any`、`any[]` 出现在业务代码中。对 `unknown` 类型使用类型守卫或 `as` 窄化到具名接口。
  - **禁止行内类型**：所有方法参数和返回值必须引用 `libs/shared/src/dto/` 或 `libs/shared/src/vo/` 中预定义的接口，不允许 `@Payload() data: { foo: string; bar: number }` 这类行内定义。
  - **DTO/VO 分层**：入站参数使用 DTO（位于 `dto/`），出站响应使用 VO（位于 `vo/`）。Service 层必须通过 `static toVO()` 工厂方法显式转换，禁止直接 `return repo.save(entity)` 透传 Entity。
  - **ID 类型统一为 `string`**：数据库 `bigint` 列在应用层一律映射为 `string`，`nextId()` 返回 `string`，Controller/Service 参数中的 ID 字段类型为 `string`。
* 开发 Agent 时，由于 PowerShell 终端特性，多行指令拼接务必使用 `;` 而非 `&&`。stderr 中捕获的 `INFO` 不等于报错。
* 后端微服务的拓展需遵守严苛的服务解耦，`auth-service` 和 `patient-service` 之间不允许反向外键，所有联合视图必须经由 API/网关重组，跨域验证需携带隔离 ID (org_id 等等)。 
* 前端 Tailwind V4 直接将 tokens 写进 `global.css` 的 `@theme` 闭包内，绝对不允许编写 `tailwind.config.js` 的复古模式。
