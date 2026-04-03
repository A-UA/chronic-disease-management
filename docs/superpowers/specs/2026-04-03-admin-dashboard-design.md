# 管理后台设计文档 — 第一期

> 创建日期：2026-04-03
> 范围：项目脚手架 + 登录认证 + 布局框架 + 控制台仪表盘 + 患者管理（增强版）

---

## 1. 项目定位

为慢病管理多租户 AI SaaS 后端配套的 B 端管理后台。第一期实现核心框架与高优业务模块，后续分期扩展知识库管理、AI 问答、成员管理、角色权限、操作审计等模块。

### 交付范围

| 期 | 模块 | 状态 |
|----|------|------|
| **第一期（本文档）** | 脚手架、登录/认证、布局框架、控制台、患者管理 | 设计中 |
| 第二期 | 知识库管理、AI 问答 | 待规划 |
| 第三期 | 成员管理、角色权限、操作审计 | 待规划 |

### 目标用户

全角色覆盖（staff / manager / admin / owner / platform_admin），通过后端动态菜单和权限控制不同角色的可见内容与操作范围。

---

## 2. 技术栈

| 类别 | 选择 | 版本 | 说明 |
|------|------|------|------|
| 构建工具 | **Vite+** | 基于 Vite 8 + Rolldown | VoidZero 统一工具链，内置 Vitest/Oxlint/Oxfmt |
| 框架 | **React** | 19 | 最新版本 |
| 语言 | **TypeScript** | 5.x | 全面类型安全 |
| UI 组件 | **antd** + **@ant-design/pro-components** | 5.x | 按需引入 ProLayout / ProTable |
| 路由 | **React Router** | v7 | SPA 模式 |
| 数据请求 | **@tanstack/react-query** | v5 | 服务端状态管理、缓存、自动重试 |
| HTTP 客户端 | **ky** | latest | 基于原生 fetch，~1kB |
| 全局状态 | **zustand** | latest | 轻量级，管理 auth 状态 |
| 图表 | **@ant-design/charts** | latest | 健康指标趋势图 |
| 代码检查 | **Oxlint** (Vite+ 内置) | — | 替代 ESLint，Rust 实现 |
| 代码格式化 | **Oxfmt** (Vite+ 内置) | — | 替代 Prettier |

---

## 3. 项目结构

前端项目位于 `frontend/` 目录，与 `backend/` 平级。

```
frontend/
├── src/
│   ├── api/                      # API 层
│   │   ├── client.ts             # ky 实例（baseURL、Token 注入、错误拦截）
│   │   ├── auth.ts               # 认证 API（登录/注册/me/菜单树）
│   │   ├── patients.ts           # 患者相关 API
│   │   ├── health-metrics.ts     # 健康指标 API
│   │   └── dashboard.ts          # 仪表盘 API
│   │
│   ├── components/               # 通用组件
│   │   ├── PageLoading.tsx       # 全局加载态
│   │   └── PermissionGuard.tsx   # 权限守卫组件
│   │
│   ├── hooks/                    # 自定义 Hooks
│   │   ├── useAuth.ts            # 认证状态（zustand store）
│   │   └── usePermission.ts      # 权限判断
│   │
│   ├── layouts/                  # 布局
│   │   └── AdminLayout.tsx       # 主布局（ProLayout + 动态菜单）
│   │
│   ├── pages/                    # 页面
│   │   ├── login/
│   │   │   └── index.tsx
│   │   ├── dashboard/
│   │   │   └── index.tsx
│   │   └── patients/
│   │       ├── index.tsx         # 患者列表
│   │       ├── [id].tsx          # 患者详情
│   │       └── components/
│   │           ├── PatientTable.tsx
│   │           ├── HealthTrendChart.tsx
│   │           └── SuggestionList.tsx
│   │
│   ├── router/                   # 路由
│   │   ├── index.tsx             # 路由入口
│   │   ├── registry.ts           # code → 模块映射注册表
│   │   ├── generateRoutes.ts     # 后端菜单 → React Router 路由生成
│   │   ├── AuthRoute.tsx         # 登录态守卫
│   │   └── modules/              # 各业务模块路由定义
│   │       ├── dashboard.tsx
│   │       └── patients.tsx
│   │
│   ├── stores/                   # zustand
│   │   └── auth.ts
│   │
│   ├── types/                    # TypeScript 类型
│   │   ├── api.ts
│   │   ├── patient.ts
│   │   └── auth.ts
│   │
│   ├── utils/
│   │   └── snowflake.ts          # 雪花 ID 处理
│   │
│   ├── App.tsx
│   └── main.tsx
│
├── package.json
└── vite.config.ts
```

### 设计原则

1. **API 层与 UI 解耦**：`api/` 只负责发请求和类型化返回值，页面通过 react-query hooks 消费
2. **按功能模块组织页面**：每个业务模块一个文件夹，私有组件就近放置
3. **权限驱动渲染**：菜单和按钮级别通过 `usePermission` hook + `PermissionGuard` 组件控制
4. **雪花 ID 处理**：后端以字符串形式返回大整数 ID，前端统一用 `string` 类型接收

---

## 4. 认证与权限

### 4.1 登录流程

```
用户输入邮箱+密码
    ↓
POST /api/v1/auth/login/access-token (OAuth2 Password Flow)
    ↓
获取 JWT access_token
    ↓
存入 zustand store + localStorage
    ↓
并行请求:
  ├── GET /api/v1/auth/me → 用户信息 + org_id + permissions[]
  └── GET /api/v1/auth/menu-tree → 动态菜单列表
    ↓
存入 auth store → 渲染主布局
```

### 4.2 Auth Store 设计

```typescript
interface AuthState {
  token: string | null;
  user: UserInfo | null;          // id, email, name, org_id
  permissions: string[];          // ["patient:read", "kb:manage", ...]
  menus: MenuItem[];              // 动态菜单树（嵌套结构）

  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchUserInfo: () => Promise<void>;
}
```

### 4.3 路由守卫

分两层：

- **AuthRoute（登录态守卫）**：未登录 → 重定向 `/login`；已登录但 user 未加载 → 调用 `fetchUserInfo()`
- **PermissionGuard（权限守卫）**：通过路由 `handle.permission` 检查用户是否拥有对应权限，无权限 → 403 页面

### 4.4 权限控制粒度

| 层级 | 实现方式 | 示例 |
|------|---------|------|
| 菜单级 | 后端 `/auth/menu-tree` 返回什么就渲染什么 | staff 看不到「成员管理」 |
| 按钮级 | `usePermission('patient:update')` hook | 无权限时隐藏「编辑」按钮 |
| API 级 | 后端 `check_permission` 兜底 | 即使前端绕过也会 403 |

### 4.5 Token 管理

- **存储**：`localStorage`（7 天有效期匹配后端配置）
- **注入**：`ky.extend()` 的 `beforeRequest` hook 自动添加 `Authorization: Bearer <token>`
- **过期处理**：`afterResponse` hook 检测 401 → 清空 store → 跳转 `/login`
- **组织上下文**：每次请求自动携带 `X-Organization-ID` header

---

## 5. 布局与动态菜单

### 5.1 主布局

使用 `ProLayout`，经典左侧导航 + 顶栏布局：

- **侧边栏**：动态菜单，支持展开/折叠，移动端自动切为抽屉模式
- **顶栏右侧**：用户头像 + 下拉（个人信息、修改密码、退出登录）
- **内容区**：React Router Outlet
- **底栏**：版权信息

### 5.2 独立 menus 表

菜单数据从 `permissions` 表的 `ui_metadata` JSONB 中**迁出**，创建独立的 `menus` 表。

#### 表结构

```
menus
├── id                BigInteger   PK (雪花 ID)
├── parent_id         BigInteger   FK → menus.id, NULLABLE
├── org_id            BigInteger   FK → organizations.id, NULLABLE
├── name              String(100)  NOT NULL        — "患者管理"
├── code              String(100)  UNIQUE NOT NULL  — "patients"
├── menu_type         String(20)   NOT NULL DEFAULT 'page'  — directory / page / link
├── path              String(255)  NULLABLE         — "/patients"
├── icon              String(50)   NULLABLE         — "TeamOutlined"
├── permission_code   String(100)  NULLABLE         — "patient:read"
├── sort              Integer      DEFAULT 0
├── is_visible        Boolean      DEFAULT TRUE     — 侧边栏是否显示
├── is_enabled        Boolean      DEFAULT TRUE     — 是否启用（灰度）
├── meta              JSONB        NULLABLE         — 扩展元信息
├── created_at        DateTime
├── updated_at        DateTime
└── deleted_at        DateTime     NULLABLE
```

#### 索引

| 索引 | 类型 | 字段 |
|------|------|------|
| `idx_menus_parent_sort` | B-tree | `(parent_id, sort)` |
| `idx_menus_org_id` | B-tree | `org_id` |
| `uq_menus_code` | UNIQUE | `code` |

#### 设计理由

- 与项目现有的 `organizations.parent_id`、`roles.parent_role_id` 树形模式一致
- 关注点分离：菜单（导航 UI）与权限（访问控制）解耦
- 支持多租户菜单定制（`org_id` 字段）
- FK 约束保证父子关系完整性

### 5.3 动态路由生成

采用**行业标准的「后端菜单 + 前端路由注册表」模式**（Ant Design Pro / vue-vben-admin / vue-element-admin 统一采用此模式）。

#### 前端路由模块注册表

```typescript
// router/registry.ts
// 键名 = menus 表的 code 字段
export const routeRegistry: Record<string, RouteModule> = {
  'dashboard':  dashboardRouteModule,
  'patients':   patientRouteModule,
  // ... 每个菜单模块注册一次
};
```

每个模块定义 `index` 页面 + `children` 子路由（含动态路由如 `:id`）：

```typescript
// router/modules/patients.tsx
export const patientRouteModule = {
  index: <PatientListPage />,
  children: [
    { path: ':id', element: <PatientDetailPage />, handle: { breadcrumb: '患者详情' } },
  ],
};
```

#### 运行时路由生成

`generateRoutes(menuTree)` 函数递归遍历后端菜单树，通过 `menu.code` 在 `routeRegistry` 中查找对应模块，将 `index` 挂为主页面、`children` 挂为子路由，生成最终的 `RouteObject[]`。

#### 权限继承

子路由（如 `/patients/:id`）无需单独声明权限，自动继承父菜单的 `permission_code`。路由守卫通过 `handle.permission` 向上查找最近的权限声明进行校验。

---

## 6. 控制台仪表盘

### 数据来源

`GET /api/v1/dashboard/stats` — 后端根据请求上下文自动返回对应范围的数据（平台级 / 租户级）。

### 页面布局

#### 统计卡片区（顶部）

使用 antd `Statistic` + `Card`，展示：

- 机构总数 / 用户总数 / 患者总数 / 对话总数
- 24h 活跃用户 / Token 消耗总量 / 失败文档数

#### Token 用量趋势图（中部）

使用 `@ant-design/charts` 的 `Line` 组件，展示近 7 天每日 Token 消耗趋势。

---

## 7. 患者管理模块

### 7.1 患者列表页

路由：`/patients`

使用 `ProTable` 组件，功能：

| 功能 | 说明 |
|------|------|
| 搜索 | 按姓名模糊搜索（`search` 参数） |
| 分页 | `skip` / `limit` 参数 |
| 列 | 姓名、性别、出生日期、创建时间、操作 |
| 新建 | `patient:create` 权限，Modal 表单 |
| 删除 | `patient:delete` 权限，二次确认 |

### 7.2 患者详情页

路由：`/patients/:id`

使用 antd `Tabs` 组件分三个标签页：

#### Tab 1：基本信息

只读展示患者档案，有 `patient:update` 权限时可编辑。

#### Tab 2：健康指标

- 指标类型选择器：blood_pressure / blood_sugar / weight / heart_rate / bmi / spo2
- 时间范围选择器：近 7 / 30 / 90 天
- 趋势折线图（血压为双线：收缩压 + 舒张压）
- 原始数据表格

#### Tab 3：管理建议

列表展示：建议内容、类型（clinical/lifestyle/general）、创建时间、管理师姓名。

### 7.3 需要后端补充的接口

| 接口 | 说明 |
|------|------|
| `GET /health-metrics/patients/{patient_id}/trend` | 管理端查看指定患者的健康指标趋势（当前只有 `/me/trend` 接口） |

---

## 8. 错误处理与全局约定

### 8.1 HTTP 错误处理

在 `ky` 实例的 `afterResponse` hook 统一处理：

| 状态码 | 行为 |
|--------|------|
| 401 | 清空 auth store → 跳转 `/login` |
| 403 | `message.error` 提示权限不足 |
| 404 | 业务提示 / NotFound 页面 |
| 422 | 解析 `detail` 字段，逐字段高亮 |
| 500 | 通用错误提示 |

### 8.2 雪花 ID 约定

- 前端所有 ID 类型定义为 `string`
- URL 拼接直接用字符串
- 比较用 `===` 字符串比较

### 8.3 加载状态

- 页面级：react-query `isLoading` + `Suspense` + `PageLoading`
- 按钮级：antd `Button.loading` 绑定 mutation `isPending`

### 8.4 QueryClient 配置

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,   // 5 分钟
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

---

## 9. 开发端口与代理

| 服务 | 端口 |
|------|------|
| 后端 API | `localhost:8000` |
| 前端 Vite+ | `localhost:5173` |

Vite+ 配置开发代理：

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
},
```

`localhost:5173` 已在后端 CORS 白名单（`CORS_ORIGINS`）中。
