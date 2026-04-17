# 慢病管理多租户 AI SaaS — 项目指南

更新时间：2026-04-16

## 1. 项目概览

面向慢病管理场景的多租户 AI SaaS 全栈项目。本项目近期经历了架构大重构，将原有的 Python 单体应用升级为**多语言微服务架构 (Polyglot Microservices)**，包含一套独立的 **Python AI Agent 中间件**，以及由 **Java/NestJS 提供双平台参考实现**的核心业务微服务，配合原有的 React 前端管理后台。

核心能力：
- **微服务/网关设计**：通过统一 Gateway 路由请求，下层拆分为 Auth Service（用户/组织/RBAC）与 Patient Service（慢病健康档案/指标/家属）。
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
- **技术栈**: TypeScript, NestJS, Prisma / TypeORM。
- **结构**: PNPM Workspace Monorepo (`gateway` / `auth-service` / `patient-service` / `shared`)。
- **服务通信**: 微服务间使用 `@nestjs/microservices` 原生 TCP 传输与消息代理通信模式，提升内网调用效率。

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
│   ├── libs/shared/               # 共享库 (Constants, DTOs, 拦截器, 配置等)
│   ├── apps/gateway/              # 转发网关与鉴权中间件
│   ├── apps/auth/                 # RBAC/租户凭证微服务 (TCP)
│   ├── apps/patient/              # 慢病数据与档案微服务 (TCP)
│   └── package.json               # PNPM + Turbo 工作区间配置
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

整体外部请求链路向微服务网关 (Gateway) 收拢，各子服务分工明确：

1. **客户端请求** → 触达 `Gateway`。
2. **鉴权**：
   - Gateway 在前置拦截器拦截 JWT，解析后获取用户所在的 Organization ID、Role 和对应具体菜单及 API Path 白名单校验。
3. **流量分发**：
   - 匹配 `/api/v1/auth` / `/api/v1/users` → 转发到 `auth-service`。
   - 匹配 `/api/v1/patients` / `/api/v1/health-metrics` → 转发到 `patient-service`。
   - 匹配 `/api/v1/chat` → Gateway 首先验证 RAG 配置、提取 `history` 上下文、拼接目前操作对象的属性数据（如 `kb_id` 等），然后以 Server 至 Server 方式请求大模型网关 `agent/internal/chat`，代理并透传后续的 SSE 数据流回调给前端。
4. **Agent 执行**：
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
- **NestJS**：在 `backend-nestjs` 运行 `pnpm install` 安装所有依赖并执行 `pnpm run build`。平时开发可使用 `pnpm run dev:auth` 等脚本单独启动服务，或直接使用 Turborepo 启动所需的子服务。（`synchronize: false`，必须先执行 5.2；TCP 微服务需先于网关启动）

### 5.5 启动前端后台
```powershell
cd frontend
vp install 
vp dev
```

## 6. 代码提交检查标准

* **数据库变更**：任何表结构修改必须同步更新 `database/init.sql`，禁止依赖 ORM 自动同步。NestJS `synchronize` 和 Java `ddl-auto` 均已锁定为关闭状态。
* 开发 Agent 时，由于 PowerShell 终端特性，多行指令拼接务必使用 `;` 而非 `&&`。stderr 中捕获的 `INFO` 不等于报错。
* 后端微服务的拓展需遵守严苛的服务解耦，`auth-service` 和 `patient-service` 之间不允许反向外键，所有联合视图必须经由 API/网关重组，跨域验证需携带隔离 ID (org_id 等等)。 
* 前端 Tailwind V4 直接将 tokens 写进 `global.css` 的 `@theme` 闭包内，绝对不允许编写 `tailwind.config.js` 的复古模式。
