# 前端后台管理系统设计规范 (Frontend Admin System Design)

**日期**：2026-03-26  
**版本**：v1.0.0  
**状态**：待审批 (Pending)  
**方案**：方案 1 - 统一权限管理门户 (Unified Management Portal)

---

## 1. 业务目标与愿景 (Business Goals & Vision)

构建一个全平台、全功能、多租户的 AI SaaS 后端管理系统，通过统一的入口满足不同层级用户（超级管理员、组织管理员、医护管理者）的差异化需求。系统核心聚焦于 **多租户治理** 与 **RAG (检索增强生成) 能力管理**。

## 2. 技术架构与技术栈 (Technology Stack)

基于 React 生态的最新、主流、高性能技术栈：

- **核心框架**：React 18/19 + Vite
- **UI 组件库**：Ant Design 5 (企业级) + Shadcn UI (局部灵活定制)
- **样式方案**：Tailwind CSS (原子化 / 响应式)
- **数据获取/同步**：TanStack Query v5 (React Query) - 提供强大的缓存与并发请求管理
- **状态管理**：Zustand (轻量级、跨组件通信)
- **路由管理**：React Router v6/v7
- **表单验证**：React Hook Form + Zod (类型安全)
- **类型系统**：TypeScript (严格模式)

## 3. 用户角色与权限模型 (RBAC Model)

系统通过 JWT 中的角色信息动态渲染视图与控制访问：

| 角色 (Role) | 访问路径前缀 | 核心能力范围 |
| :--- | :--- | :--- |
| **超级管理员 (SUPER_ADMIN)** | `/admin/*` | 跨租户(Org)管理、全局额度配额、全平台审计、系统级配置。 |
| **组织管理员 (ORG_ADMIN)** | `/org/*` | 本机构职员(Manager)管理、机构级 RBAC 授权、机构知识库策略、数据看板。 |
| **医护管理者 (MANAGER)** | `/biz/*` | 患者档案全生命周期管理、RAG 辅助对话、个人会话追溯、家属权限分配。 |

- **路由保护**：基于 React Router 的 `Loader` 拦截非法越权访问。
- **组件保护**：使用 `<Access roles={...}>` 高阶组件控制按钮或视图的可见性。

## 4. 核心功能模块 (Core Functional Modules)

### 4.1 超级管理模块 (Admin)
- **组织中心 (Org Center)**：机构入驻、账户冻结、到期管理。
- **配额控制 (Quota Console)**：集中管理各机构的 LLM Token 限制、存储空间及 API Keys。
- **全局审计 (Global Audit)**：全链路操作追踪。

### 4.2 组织治理模块 (Org)
- **成员中心 (Staff Admin)**：医护人员账号管理与角色分配。
- **机构知识中心 (Org KB Center)**：初始化知识库、设置全局 Reranker 阈值、管理 Embedding 服务。
- **效能分析 (Data Analytics)**：知识库覆盖度、AI 回答采纳率、资源消耗分布。

### 4.3 业务/医疗操作模块 (Biz)
- **患者工作台 (Patient Workbench)**：健康档案视图、动态病历跟踪、家属关联。
- **AI 助手 (RAG Assistant)**：支持多格式文档上传、检索过程可视化预览、引用化（Citation）对话。
- **对话回溯 (Session History)**：详细查看每轮 AI 决策的证据 (Evidence) 与不确定性 (Uncertainty)。

## 5. 数据流与 RAG 交互设计 (Data Flow & RAG Interaction)

### 5.1 数据同步逻辑
- 使用 **TanStack Query** 实现“自动失效 -> 重新获取”机制（如：上传文档后自动刷新列表）。
- 对高频操作（如：启用/禁用用户、标记患者状态）采用 **乐观更新 (Optimistic UI)** 提升交互响应速度。

### 5.2 RAG 深度交互
- **引用化预览 (Citation Preview)**：点击回复中的 `[Doc n]`，侧边栏联动高亮显示原始文档片段。
- **解析状态监控**：实时展示文档解析进度，对 `failed_reason` 进行人性化报错与一键重试。

## 6. UI/UX 设计原则 (Design Principles)

- **一致性**：遵循 Ant Design 5 的设计规范，保证跨角色的组件感官统一。
- **响应式**：侧端侧重 PC 端操作，适配常见平板电脑。
- **效率优先**：大量使用快捷键支持与多列筛选表格。
- **透明性**：RAG 检索过程应对管理员和管理者可见（Debug 模式），方便质量调优。

---

## 7. 下一步行动 (Next Steps)

1. **环境准备**：搭建 Vite + React + Ant Design 项目模板。
2. **Schema 对齐**：从后端 `openapi.json` 生成 TypeScript 类型定义。
3. **路由骨架**：基于角色层级搭建主导航与侧边栏骨架。
4. **原型开发**：优先实现登录与组织管理/知识库管理的 MVP 版本。
