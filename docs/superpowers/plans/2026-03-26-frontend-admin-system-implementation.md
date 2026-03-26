# 前端管理系统实施计划 (Frontend Admin System Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 React + Ant Design 构建全平台全功能管理后台，支持多租户 RBAC 与 RAG 深度交互。

**Architecture:** 统一门户架构，根据 JWT 角色动态渲染菜单与路由。使用 TanStack Query 管理服务端状态，Zustand 管理本地状态。

**Tech Stack:** React 18+, Vite, Ant Design 5, Tailwind CSS, TanStack Query v5, Zustand, React Router v6.

---

### Task 1: 项目初始化与基础配置

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: 创建 package.json 并安装核心依赖**

```json
{
  "name": "chronic-disease-management-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.22.3",
    "antd": "^5.15.3",
    "zustand": "^4.5.2",
    "@tanstack/react-query": "^5.28.9",
    "axios": "^1.6.8",
    "lucide-react": "^0.363.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.2"
  },
  "devDependencies": {
    "@types/react": "^18.2.66",
    "@types/react-dom": "^18.2.22",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.2.2",
    "vite": "^5.2.2",
    "tailwindcss": "^3.4.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38"
  }
}
```

- [ ] **Step 2: 配置 vite.config.ts 支持 API 代理**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

- [ ] **Step 3: 初始化 Tailwind CSS**

运行: `npx tailwindcss init -p`

- [ ] **Step 4: 提交**

```bash
git add frontend/
git commit -m "chore: init frontend project with vite and react"
```

---

### Task 2: API 客户端与类型生成

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/scripts/generate-types.ts`

- [ ] **Step 1: 编写 Axios 基础客户端**

```typescript
import axios from 'axios';

const client = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default client;
```

- [ ] **Step 2: 配置 OpenAPI 类型生成脚本**

使用 `openapi-typescript` 库。

- [ ] **Step 3: 运行脚本生成类型**

运行: `npx openapi-typescript http://localhost:8000/api/v1/openapi.json -o frontend/src/api/types.ts`

- [ ] **Step 4: 提交**

```bash
git add frontend/src/api/
git commit -m "feat: add api client and generate types"
```

---

### Task 3: 认证管理与登录页面

**Files:**
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/pages/login/LoginPage.tsx`

- [ ] **Step 1: 实现 Auth Store (Zustand)**

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  user: any | null;
  token: string | null;
  setAuth: (user: any, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setAuth: (user, token) => {
        localStorage.setItem('auth_token', token);
        set({ user, token });
      },
      logout: () => {
        localStorage.removeItem('auth_token');
        set({ user: null, token: null });
      },
    }),
    { name: 'auth-storage' }
  )
);
```

- [ ] **Step 2: 编写基于 Ant Design 的登录页面**

实现用户名密码登录，调用 `/auth/login` 接口。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/stores/auth.ts frontend/src/pages/login/
git commit -m "feat: add auth store and login page"
```

---

### Task 4: 主布局与路由守卫

**Files:**
- Create: `frontend/src/components/layout/MainLayout.tsx`
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: 实现响应式侧边栏布局**

根据 `authStore.user.roles` 渲染不同的 `Menu` 项。

- [ ] **Step 2: 编写路由守卫组件**

```tsx
const ProtectedRoute = ({ children, allowedRoles }: { children: React.ReactNode, allowedRoles?: string[] }) => {
  const { user, token } = useAuthStore();
  if (!token) return <Navigate to="/login" />;
  if (allowedRoles && !allowedRoles.some(r => user?.roles?.includes(r))) {
    return <Navigate to="/403" />;
  }
  return <>{children}</>;
};
```

- [ ] **Step 3: 配置根路由结构**

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/layout/ frontend/src/App.tsx
git commit -m "feat: implement main layout and route guards"
```

---

### Task 5: 组织管理功能 (超级管理员)

**Files:**
- Create: `frontend/src/pages/admin/OrgManagement.tsx`

- [ ] **Step 1: 编写组织列表表格**

使用 `TanStack Query` 获取 `/admin/organizations` 数据。展示名称、ID、状态、创建时间。

- [ ] **Step 2: 实现创建/编辑组织弹窗**

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/admin/OrgManagement.tsx
git commit -m "feat: add organization management for super admin"
```

---

### Task 6: 知识库与文档管理 (RAG UI)

**Files:**
- Create: `frontend/src/pages/org/KBManagement.tsx`
- Create: `frontend/src/components/rag/DocUpload.tsx`

- [ ] **Step 1: 实现文档上传与解析状态展示**

调用 `/documents/upload` 接口，轮询展示解析进度。

- [ ] **Step 2: 知识库关联与搜索预览**

展示知识库列表，支持简单的检索测试功能。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/org/KBManagement.tsx frontend/src/components/rag/
git commit -m "feat: implement document upload and KB management UI"
```

---

### Task 7: 患者工作台与引用化对话

**Files:**
- Create: `frontend/src/pages/biz/PatientWorkbench.tsx`
- Create: `frontend/src/components/chat/ChatPane.tsx`

- [ ] **Step 1: 患者档案列表与详情页**

- [ ] **Step 2: 实现引用化 AI 对话组件**

支持流式输出 (`SSE`)。对消息中的引用 `[Doc n]` 实现点击跳转至来源片段的功能。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/biz/ frontend/src/components/chat/
git commit -m "feat: add patient workbench and RAG chat assistant"
```
