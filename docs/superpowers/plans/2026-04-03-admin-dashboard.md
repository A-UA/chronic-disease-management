# 管理后台第一期实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为慢病管理后端构建 B 端管理后台第一期（脚手架 + 登录 + 布局 + 仪表盘 + 患者管理）

**Architecture:** 后端新增 menus 表和菜单树 API，前端基于 Vite+ / React 19 / antd 构建 SPA，通过后端动态菜单驱动侧边栏导航，react-query 管理服务端状态，zustand 管理认证状态。

**Tech Stack:** Vite+ (Vite 8), React 19, TypeScript 5, antd 5, @ant-design/pro-components, React Router v7, @tanstack/react-query v5, ky, zustand, @ant-design/charts

**Spec:** `docs/superpowers/specs/2026-04-03-admin-dashboard-design.md`

---

## 文件结构总览

### 后端（新增/修改）

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `backend/app/db/models/menu.py` | Menu ORM 模型 |
| 修改 | `backend/app/db/models/__init__.py` | 导出 Menu |
| 新建 | `backend/alembic/versions/xxxx_add_menus_table.py` | 迁移脚本（自动生成） |
| 新建 | `backend/app/db/seed_menus.py` | 菜单种子数据 |
| 新建 | `backend/app/schemas/menu.py` | 菜单响应模型 |
| 修改 | `backend/app/api/endpoints/auth.py:142-180` | 重写 menu-tree 端点，从 menus 表读取 |
| 修改 | `backend/app/api/endpoints/health_metrics.py` | 新增管理端趋势查询接口 |

### 前端（全部新建）

| 文件 | 职责 |
|------|------|
| `frontend/vite.config.ts` | Vite+ 配置（代理） |
| `frontend/src/api/client.ts` | ky 实例（Token 注入、错误拦截） |
| `frontend/src/api/auth.ts` | 认证 API |
| `frontend/src/api/dashboard.ts` | 仪表盘 API |
| `frontend/src/api/patients.ts` | 患者 API |
| `frontend/src/api/health-metrics.ts` | 健康指标 API |
| `frontend/src/types/api.ts` | 通用响应类型 |
| `frontend/src/types/auth.ts` | 认证相关类型 |
| `frontend/src/types/patient.ts` | 患者相关类型 |
| `frontend/src/stores/auth.ts` | zustand 认证 store |
| `frontend/src/hooks/usePermission.ts` | 权限判断 hook |
| `frontend/src/utils/menu-tree.ts` | 菜单树构建工具函数 |
| `frontend/src/router/index.tsx` | 路由入口 |
| `frontend/src/router/registry.ts` | code → 模块注册表 |
| `frontend/src/router/generateRoutes.ts` | 动态路由生成 |
| `frontend/src/router/AuthRoute.tsx` | 登录态守卫 |
| `frontend/src/router/modules/dashboard.tsx` | 仪表盘路由模块 |
| `frontend/src/router/modules/patients.tsx` | 患者路由模块 |
| `frontend/src/layouts/AdminLayout.tsx` | ProLayout 主布局 |
| `frontend/src/components/PageLoading.tsx` | 全局加载组件 |
| `frontend/src/components/PermissionGuard.tsx` | 权限守卫组件 |
| `frontend/src/pages/login/index.tsx` | 登录页 |
| `frontend/src/pages/dashboard/index.tsx` | 仪表盘页 |
| `frontend/src/pages/patients/index.tsx` | 患者列表页 |
| `frontend/src/pages/patients/[id].tsx` | 患者详情页 |
| `frontend/src/pages/patients/components/HealthTrendChart.tsx` | 健康趋势图 |
| `frontend/src/pages/patients/components/SuggestionList.tsx` | 管理建议列表 |
| `frontend/src/pages/403.tsx` | 无权限页面 |
| `frontend/src/pages/404.tsx` | 未找到页面 |
| `frontend/src/App.tsx` | 根组件 |
| `frontend/src/main.tsx` | 入口文件 |

---

## Task 1: 后端 — Menu ORM 模型

**Files:**
- Create: `backend/app/db/models/menu.py`
- Modify: `backend/app/db/models/__init__.py`

- [ ] **Step 1: 创建 Menu 模型文件**

```python
# backend/app/db/models/menu.py
from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin


class Menu(Base, IDMixin, TimestampMixin):
    __tablename__ = "menus"

    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("menus.id", ondelete="CASCADE"), nullable=True
    )
    org_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="菜单显示名称")
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="菜单唯一编码")
    menu_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="page", comment="directory/page/link"
    )
    path: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="路由路径或外部URL")
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="图标名称")
    permission_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="关联权限编码"
    )
    sort: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, comment="侧边栏是否显示")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="扩展元信息")

    # 自引用关系
    children: Mapped[list[Menu]] = relationship(
        "Menu", back_populates="parent", cascade="all, delete-orphan",
        order_by="Menu.sort",
    )
    parent: Mapped[Menu | None] = relationship(
        "Menu", back_populates="children", remote_side="Menu.id"
    )

    __table_args__ = (
        Index("idx_menus_parent_sort", "parent_id", "sort"),
        Index("idx_menus_org_id", "org_id"),
    )
```

- [ ] **Step 2: 注册到 models/__init__.py**

在 `backend/app/db/models/__init__.py` 中添加导入：

```python
# 在现有导入末尾添加
from .menu import Menu

# 在 __all__ 列表末尾添加
    "Menu",
```

- [ ] **Step 3: 提交**

```bash
cd backend
git add app/db/models/menu.py app/db/models/__init__.py
git commit -m "feat(backend): 新增 Menu ORM 模型"
```

---

## Task 2: 后端 — Alembic 迁移

**Files:**
- Create: `backend/alembic/versions/xxxx_add_menus_table.py`（自动生成）

- [ ] **Step 1: 生成迁移脚本**

```bash
cd backend
uv run alembic revision --autogenerate -m "add_menus_table"
```

- [ ] **Step 2: 检查生成的迁移脚本**

打开生成的迁移文件，确认包含：
- `create_table('menus', ...)` 包含所有字段
- `create_index('idx_menus_parent_sort', ...)`
- `create_index('idx_menus_org_id', ...)`
- `create_foreign_key` 对 `parent_id` 和 `org_id`

- [ ] **Step 3: 执行迁移**

```bash
uv run alembic upgrade head
```

预期输出：`INFO  [alembic.runtime.migration] Running upgrade ... -> ..., add_menus_table`

- [ ] **Step 4: 提交**

```bash
git add alembic/versions/
git commit -m "feat(backend): 菜单表迁移脚本"
```

---

## Task 3: 后端 — 菜单种子数据 + 响应模型

**Files:**
- Create: `backend/app/db/seed_menus.py`
- Create: `backend/app/schemas/menu.py`

- [ ] **Step 1: 创建菜单响应模型**

```python
# backend/app/schemas/menu.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Optional


class MenuRead(BaseModel):
    id: int
    name: str
    code: str
    menu_type: str
    path: Optional[str] = None
    icon: Optional[str] = None
    permission_code: Optional[str] = None
    sort: int = 0
    is_visible: bool = True
    is_enabled: bool = True
    meta: Optional[dict] = None
    children: list[MenuRead] = []

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: 创建菜单种子数据脚本**

```python
# backend/app/db/seed_menus.py
import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models.menu import Menu

SYSTEM_MENUS = [
    # 一级菜单
    {"code": "dashboard", "name": "控制台", "menu_type": "page", "path": "/dashboard",
     "icon": "DashboardOutlined", "sort": 1, "permission_code": None},

    {"code": "patient-mgmt", "name": "患者管理", "menu_type": "directory", "path": "/patients",
     "icon": "TeamOutlined", "sort": 2, "permission_code": None},

    {"code": "kb-mgmt", "name": "知识库管理", "menu_type": "directory", "path": "/knowledge",
     "icon": "BookOutlined", "sort": 3, "permission_code": "kb:manage"},

    {"code": "ai-chat", "name": "AI 问答", "menu_type": "page", "path": "/chat",
     "icon": "MessageOutlined", "sort": 4, "permission_code": "chat:use"},

    {"code": "member-mgmt", "name": "成员管理", "menu_type": "page", "path": "/members",
     "icon": "UserOutlined", "sort": 5, "permission_code": "org_member:manage"},

    {"code": "role-mgmt", "name": "角色权限", "menu_type": "page", "path": "/roles",
     "icon": "SafetyCertificateOutlined", "sort": 6, "permission_code": "org_member:manage"},

    {"code": "audit-logs", "name": "操作审计", "menu_type": "page", "path": "/audit-logs",
     "icon": "FileSearchOutlined", "sort": 7, "permission_code": "audit_log:read"},
]

# 二级菜单（parent_code → children）
CHILD_MENUS = {
    "patient-mgmt": [
        {"code": "patient-list", "name": "患者列表", "menu_type": "page", "path": "/patients",
         "sort": 1, "permission_code": "patient:read"},
        {"code": "patient-metrics", "name": "健康指标", "menu_type": "page", "path": "/patients/metrics",
         "sort": 2, "permission_code": "patient:read"},
        {"code": "patient-suggestions", "name": "管理建议", "menu_type": "page", "path": "/patients/suggestions",
         "sort": 3, "permission_code": "suggestion:read"},
    ],
    "kb-mgmt": [
        {"code": "kb-list", "name": "知识库列表", "menu_type": "page", "path": "/knowledge",
         "sort": 1, "permission_code": "kb:manage"},
        {"code": "kb-documents", "name": "文档管理", "menu_type": "page", "path": "/knowledge/documents",
         "sort": 2, "permission_code": "doc:manage"},
    ],
}


async def seed_menus():
    async with AsyncSessionLocal() as db:
        print("--- Menu Seeding Started ---")

        parent_map = {}
        for menu_data in SYSTEM_MENUS:
            stmt = select(Menu).where(Menu.code == menu_data["code"])
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if not existing:
                menu = Menu(**menu_data)
                db.add(menu)
                await db.flush()
                parent_map[menu.code] = menu.id
                print(f"  Created menu: {menu.name} ({menu.code})")
            else:
                parent_map[existing.code] = existing.id
                print(f"  Exists: {existing.name} ({existing.code})")

        for parent_code, children in CHILD_MENUS.items():
            parent_id = parent_map.get(parent_code)
            if not parent_id:
                print(f"  WARNING: Parent {parent_code} not found, skipping children")
                continue
            for child_data in children:
                stmt = select(Menu).where(Menu.code == child_data["code"])
                existing = (await db.execute(stmt)).scalar_one_or_none()
                if not existing:
                    child = Menu(parent_id=parent_id, **child_data)
                    db.add(child)
                    print(f"    Created child: {child.name} ({child.code})")

        await db.commit()
        print("--- Menu Seeding Done ---")


if __name__ == "__main__":
    asyncio.run(seed_menus())
```

- [ ] **Step 3: 运行种子脚本**

```bash
cd backend
uv run python -m app.db.seed_menus
```

预期输出：每个菜单显示 `Created menu:` 或 `Exists:`

- [ ] **Step 4: 提交**

```bash
git add app/db/seed_menus.py app/schemas/menu.py
git commit -m "feat(backend): 菜单种子数据和响应模型"
```

---

## Task 4: 后端 — 重写菜单树 API + 管理端健康指标接口

**Files:**
- Modify: `backend/app/api/endpoints/auth.py:142-180`
- Modify: `backend/app/api/endpoints/health_metrics.py`
- Modify: `backend/app/schemas/rbac.py`

- [ ] **Step 1: 重写 /auth/menu-tree 端点**

替换 `backend/app/api/endpoints/auth.py` 中第 142-180 行的 `get_menu_tree` 函数：

```python
@router.get("/menu-tree", response_model=list[MenuTreeRead])
async def get_menu_tree(
    db: AsyncSession = Depends(get_db),
    org_user: OrganizationUser = Depends(get_current_org_user),
) -> Any:
    """获取当前用户的动态导航菜单（从 menus 表读取，树形嵌套返回）"""
    from app.db.models.menu import Menu
    from app.schemas.menu import MenuRead as MenuTreeRead

    # 1. 计算用户的所有有效权限编码
    role_ids = [r.id for r in org_user.rbac_roles]
    all_role_ids = await RBACService.get_all_role_ids(db, role_ids)

    stmt = (
        select(Permission.code)
        .join(Permission.roles)
        .where(Role.id.in_(list(all_role_ids)))
        .distinct()
    )
    result = await db.execute(stmt)
    user_permission_codes = {row[0] for row in result.all()}

    # 2. 查询所有系统级菜单（org_id IS NULL）+ 本租户定制菜单
    stmt = (
        select(Menu)
        .where(
            Menu.is_enabled == True,
            Menu.deleted_at.is_(None),
            (Menu.org_id.is_(None)) | (Menu.org_id == org_user.org_id),
        )
        .order_by(Menu.sort)
    )
    result = await db.execute(stmt)
    all_menus = result.scalars().all()

    # 3. 过滤权限：无 permission_code 的菜单所有人可见，有的需匹配
    visible_menus = []
    for menu in all_menus:
        if not menu.permission_code or menu.permission_code in user_permission_codes:
            visible_menus.append(menu)

    # 4. 组装树形结构
    menu_map = {m.id: {**MenuTreeRead.model_validate(m).model_dump(), "children": []} for m in visible_menus}
    roots = []
    visible_ids = {m.id for m in visible_menus}

    for m in visible_menus:
        node = menu_map[m.id]
        if m.parent_id and m.parent_id in visible_ids:
            menu_map[m.parent_id]["children"].append(node)
        else:
            roots.append(node)

    # 5. 移除没有子节点的 directory 类型菜单
    def prune(items):
        return [
            item for item in items
            if item["menu_type"] != "directory" or len(item.get("children", [])) > 0
        ]

    return prune(roots)
```

需要导入 `MenuTreeRead`，在文件头部添加：

```python
from app.schemas.menu import MenuRead as MenuTreeRead
```

- [ ] **Step 2: 新增管理端健康指标趋势接口**

在 `backend/app/api/endpoints/health_metrics.py` 末尾追加：

```python
from app.api.deps import check_permission


@router.get("/patients/{patient_id}/trend")
async def get_patient_trend(
    patient_id: int,
    metric_type: str,
    days: int = 30,
    _perm=Depends(check_permission("patient:read")),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """[管理端] 查看指定患者的健康指标趋势"""
    from datetime import timedelta, timezone

    patient = await db.get(PatientProfile, patient_id)
    if not patient or patient.org_id != org_id:
        raise HTTPException(status_code=404, detail="Patient not found")

    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(HealthMetric)
        .where(
            HealthMetric.patient_id == patient_id,
            HealthMetric.metric_type == metric_type,
            HealthMetric.measured_at >= since,
        )
        .order_by(HealthMetric.measured_at.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()
```

- [ ] **Step 3: 提交**

```bash
cd backend
git add app/api/endpoints/auth.py app/api/endpoints/health_metrics.py app/schemas/menu.py
git commit -m "feat(backend): 重写菜单树API为menus表驱动 + 管理端健康指标趋势接口"
```

---

## Task 5: 前端 — 项目初始化

**Files:**
- Create: `frontend/` 目录及所有初始文件

- [ ] **Step 1: 安装 Vite+ CLI**

```powershell
irm https://viteplus.dev/install.ps1 | iex
```

安装完成后新开终端验证：`vp help`

- [ ] **Step 2: 创建项目**

```bash
cd d:\codes\chronic-disease-management
vp create frontend
```

交互选项选择：
- Framework: **React**
- Variant: **TypeScript**

如果 `vp create` 不可用，回退到标准 Vite：

```bash
npm create vite@latest frontend -- --template react-ts
```

- [ ] **Step 3: 安装业务依赖**

```bash
cd frontend
npm install antd @ant-design/pro-components @ant-design/icons @ant-design/charts react-router-dom@7 @tanstack/react-query ky zustand
```

- [ ] **Step 4: 安装开发依赖**

```bash
npm install -D @types/react @types/react-dom
```

- [ ] **Step 5: 配置 vite.config.ts**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 6: 配置 tsconfig 路径别名**

在 `frontend/tsconfig.json`（或 `tsconfig.app.json`）的 `compilerOptions` 中添加：

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

- [ ] **Step 7: 验证项目启动**

```bash
cd frontend
npm run dev
```

预期：浏览器访问 `http://localhost:5173` 显示 Vite + React 默认页面。

- [ ] **Step 8: 提交**

```bash
cd d:\codes\chronic-disease-management
git add frontend/
git commit -m "feat(frontend): 初始化 Vite + React + TypeScript 项目"
```

---

## Task 6: 前端 — API 客户端 + 类型定义

**Files:**
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/types/auth.ts`
- Create: `frontend/src/types/patient.ts`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: 创建通用 API 类型**

```typescript
// frontend/src/types/api.ts
export interface ApiError {
  detail: string;
}

export interface PaginatedParams {
  skip?: number;
  limit?: number;
  search?: string;
}
```

- [ ] **Step 2: 创建认证相关类型**

```typescript
// frontend/src/types/auth.ts
export interface LoginRequest {
  username: string; // OAuth2 表单用 username 字段传邮箱
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  id: string;
  email: string;
  name: string | null;
  org_id: string | null;
  permissions: string[];
}

export interface MenuItem {
  id: string;
  name: string;
  code: string;
  menu_type: 'directory' | 'page' | 'link';
  path: string | null;
  icon: string | null;
  permission_code: string | null;
  sort: number;
  is_visible: boolean;
  is_enabled: boolean;
  meta: Record<string, unknown> | null;
  children: MenuItem[];
}
```

- [ ] **Step 3: 创建患者相关类型**

```typescript
// frontend/src/types/patient.ts
export interface PatientProfile {
  id: string;
  user_id: string;
  org_id: string;
  real_name: string | null;
  gender: string | null;
  birth_date: string | null;
  medical_history: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface HealthMetric {
  id: string;
  patient_id: string;
  metric_type: string;
  value: number;
  value_secondary: number | null;
  unit: string;
  measured_at: string;
  note: string | null;
  created_at: string;
}

export interface ManagementSuggestion {
  id: string;
  patient_id: string;
  manager_id: string;
  suggestion_type: string;
  content: string;
  created_at: string;
}
```

- [ ] **Step 4: 创建 ky 客户端实例**

```typescript
// frontend/src/api/client.ts
import ky from 'ky';

const TOKEN_KEY = 'cdm_token';
const ORG_KEY = 'cdm_org_id';

export const apiClient = ky.create({
  prefixUrl: '/api/v1',
  timeout: 30000,
  hooks: {
    beforeRequest: [
      (request) => {
        const token = localStorage.getItem(TOKEN_KEY);
        if (token) {
          request.headers.set('Authorization', `Bearer ${token}`);
        }
        const orgId = localStorage.getItem(ORG_KEY);
        if (orgId) {
          request.headers.set('X-Organization-ID', orgId);
        }
      },
    ],
    afterResponse: [
      async (_request, _options, response) => {
        if (response.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(ORG_KEY);
          window.location.href = '/login';
        }
      },
    ],
  },
});

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ORG_KEY);
}

export function setOrgId(orgId: string) {
  localStorage.setItem(ORG_KEY, orgId);
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
```

- [ ] **Step 5: 提交**

```bash
cd frontend
git add src/types/ src/api/client.ts
git commit -m "feat(frontend): API 客户端和类型定义"
```

---

## Task 7: 前端 — Auth Store + API + 权限 Hook

**Files:**
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/hooks/usePermission.ts`

- [ ] **Step 1: 创建认证 API 函数**

```typescript
// frontend/src/api/auth.ts
import { apiClient } from './client';
import type { TokenResponse, UserInfo, MenuItem } from '@/types/auth';

export async function loginApi(username: string, password: string): Promise<TokenResponse> {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  return apiClient.post('auth/login/access-token', {
    body: formData,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  }).json<TokenResponse>();
}

export async function getMeApi(): Promise<UserInfo> {
  return apiClient.get('auth/me').json<UserInfo>();
}

export async function getMenuTreeApi(): Promise<MenuItem[]> {
  return apiClient.get('auth/menu-tree').json<MenuItem[]>();
}
```

- [ ] **Step 2: 创建 zustand Auth Store**

```typescript
// frontend/src/stores/auth.ts
import { create } from 'zustand';
import { loginApi, getMeApi, getMenuTreeApi } from '@/api/auth';
import { setToken, clearToken, setOrgId, getStoredToken } from '@/api/client';
import type { UserInfo, MenuItem } from '@/types/auth';

interface AuthState {
  token: string | null;
  user: UserInfo | null;
  menus: MenuItem[];
  permissions: string[];
  loading: boolean;

  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchUserInfo: () => Promise<void>;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user: null,
  menus: [],
  permissions: [],
  loading: false,

  hydrate: () => {
    const token = getStoredToken();
    if (token) {
      set({ token });
    }
  },

  login: async (email, password) => {
    const res = await loginApi(email, password);
    setToken(res.access_token);
    set({ token: res.access_token });
    await get().fetchUserInfo();
  },

  logout: () => {
    clearToken();
    set({ token: null, user: null, menus: [], permissions: [] });
  },

  fetchUserInfo: async () => {
    set({ loading: true });
    try {
      const [user, menus] = await Promise.all([getMeApi(), getMenuTreeApi()]);
      if (user.org_id) {
        setOrgId(String(user.org_id));
      }
      set({
        user,
        menus,
        permissions: user.permissions ?? [],
        loading: false,
      });
    } catch {
      get().logout();
      set({ loading: false });
    }
  },
}));
```

- [ ] **Step 3: 创建权限判断 Hook**

```typescript
// frontend/src/hooks/usePermission.ts
import { useAuthStore } from '@/stores/auth';
import { useCallback } from 'react';

export function usePermission() {
  const permissions = useAuthStore((s) => s.permissions);

  const hasPermission = useCallback(
    (code: string) => permissions.includes(code),
    [permissions],
  );

  return { hasPermission, permissions };
}
```

- [ ] **Step 4: 提交**

```bash
cd frontend
git add src/api/auth.ts src/stores/auth.ts src/hooks/usePermission.ts
git commit -m "feat(frontend): Auth Store、认证API、权限Hook"
```

---

## Task 8: 前端 — 路由基础设施

**Files:**
- Create: `frontend/src/router/generateRoutes.ts`
- Create: `frontend/src/router/registry.ts`
- Create: `frontend/src/router/AuthRoute.tsx`
- Create: `frontend/src/router/modules/dashboard.tsx`
- Create: `frontend/src/router/modules/patients.tsx`
- Create: `frontend/src/pages/403.tsx`
- Create: `frontend/src/pages/404.tsx`

- [ ] **Step 1: 创建动态路由生成函数**

```typescript
// frontend/src/router/generateRoutes.ts
import type { RouteObject } from 'react-router-dom';
import type { MenuItem } from '@/types/auth';
import { routeRegistry } from './registry';

function stripLeadingSlash(path: string | null): string {
  if (!path) return '';
  return path.startsWith('/') ? path.slice(1) : path;
}

export function generateRoutes(menus: MenuItem[]): RouteObject[] {
  return menus
    .filter((menu) => menu.menu_type !== 'link' && menu.is_visible)
    .map((menu) => {
      const mod = routeRegistry[menu.code];

      if (menu.menu_type === 'directory') {
        return {
          path: stripLeadingSlash(menu.path),
          handle: { permission: menu.permission_code, menuCode: menu.code },
          children: [
            ...generateRoutes(menu.children ?? []),
            ...(mod?.children ?? []),
          ],
        } satisfies RouteObject;
      }

      return {
        path: stripLeadingSlash(menu.path),
        handle: { permission: menu.permission_code, menuCode: menu.code },
        children: [
          { index: true, element: mod?.index ?? null },
          ...(mod?.children ?? []),
        ],
      } satisfies RouteObject;
    });
}
```

- [ ] **Step 2: 创建路由模块注册表**

```typescript
// frontend/src/router/registry.ts
import type { RouteObject } from 'react-router-dom';
import { lazy, type ReactNode } from 'react';

export interface RouteModule {
  index: ReactNode;
  children?: RouteObject[];
}

const DashboardPage = lazy(() => import('@/pages/dashboard/index'));
const PatientListPage = lazy(() => import('@/pages/patients/index'));
const PatientDetailPage = lazy(() => import('@/pages/patients/[id]'));

export const routeRegistry: Record<string, RouteModule> = {
  'dashboard': {
    index: <DashboardPage />,
    children: [],
  },
  'patient-list': {
    index: <PatientListPage />,
    children: [
      { path: ':id', element: <PatientDetailPage />, handle: { breadcrumb: '患者详情' } },
    ],
  },
};
```

- [ ] **Step 3: 创建 AuthRoute 登录守卫**

```typescript
// frontend/src/router/AuthRoute.tsx
import { useEffect } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/auth';
import PageLoading from '@/components/PageLoading';

export default function AuthRoute() {
  const { token, user, loading, fetchUserInfo, hydrate } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const currentToken = useAuthStore((s) => s.token);

  useEffect(() => {
    if (currentToken && !user && !loading) {
      fetchUserInfo();
    }
  }, [currentToken, user, loading, fetchUserInfo]);

  if (!currentToken) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (loading || !user) {
    return <PageLoading />;
  }

  return <Outlet />;
}
```

- [ ] **Step 4: 创建 403 / 404 页面**

```typescript
// frontend/src/pages/403.tsx
import { Button, Result } from 'antd';
import { useNavigate } from 'react-router-dom';

export default function Forbidden() {
  const navigate = useNavigate();
  return (
    <Result
      status="403"
      title="403"
      subTitle="抱歉，您没有权限访问此页面"
      extra={<Button type="primary" onClick={() => navigate('/')}>返回首页</Button>}
    />
  );
}
```

```typescript
// frontend/src/pages/404.tsx
import { Button, Result } from 'antd';
import { useNavigate } from 'react-router-dom';

export default function NotFound() {
  const navigate = useNavigate();
  return (
    <Result
      status="404"
      title="404"
      subTitle="抱歉，您访问的页面不存在"
      extra={<Button type="primary" onClick={() => navigate('/')}>返回首页</Button>}
    />
  );
}
```

- [ ] **Step 5: 创建 PageLoading 组件**

```typescript
// frontend/src/components/PageLoading.tsx
import { Spin } from 'antd';

export default function PageLoading() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <Spin size="large" />
    </div>
  );
}
```

- [ ] **Step 6: 提交**

```bash
cd frontend
git add src/router/ src/pages/403.tsx src/pages/404.tsx src/components/PageLoading.tsx
git commit -m "feat(frontend): 路由基础设施（动态路由生成、守卫、注册表）"
```

---

## Task 9: 前端 — AdminLayout 主布局

**Files:**
- Create: `frontend/src/layouts/AdminLayout.tsx`

- [ ] **Step 1: 创建主布局组件**

```typescript
// frontend/src/layouts/AdminLayout.tsx
import { Suspense } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { ProLayout } from '@ant-design/pro-components';
import { LogoutOutlined, UserOutlined } from '@ant-design/icons';
import { Dropdown, message } from 'antd';
import * as Icons from '@ant-design/icons';
import { useAuthStore } from '@/stores/auth';
import PageLoading from '@/components/PageLoading';
import type { MenuItem } from '@/types/auth';

// 将后端菜单树转为 ProLayout 的 route 格式
function menusToRoutes(menus: MenuItem[]): any[] {
  return menus
    .filter((m) => m.is_visible)
    .map((menu) => {
      const IconComp = menu.icon ? (Icons as any)[menu.icon] : undefined;
      return {
        path: menu.path ?? '/',
        name: menu.name,
        icon: IconComp ? <IconComp /> : undefined,
        children: menu.children?.length ? menusToRoutes(menu.children) : undefined,
      };
    });
}

export default function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, menus, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    message.success('已退出登录');
    navigate('/login');
  };

  return (
    <ProLayout
      title="慢病管理系统"
      layout="mix"
      fixSiderbar
      route={{ routes: menusToRoutes(menus) }}
      location={{ pathname: location.pathname }}
      menu={{ type: 'sub' }}
      menuItemRender={(item, dom) => (
        <div onClick={() => item.path && navigate(item.path)}>{dom}</div>
      )}
      avatarProps={{
        icon: <UserOutlined />,
        title: user?.name || user?.email || '用户',
        render: (_props, dom) => (
          <Dropdown
            menu={{
              items: [
                { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
              ],
            }}
          >
            {dom}
          </Dropdown>
        ),
      }}
      footerRender={() => (
        <div style={{ textAlign: 'center', padding: 16, color: '#999' }}>
          © 2026 慢病管理系统
        </div>
      )}
    >
      <Suspense fallback={<PageLoading />}>
        <Outlet />
      </Suspense>
    </ProLayout>
  );
}
```

- [ ] **Step 2: 提交**

```bash
cd frontend
git add src/layouts/AdminLayout.tsx
git commit -m "feat(frontend): AdminLayout 主布局（ProLayout + 动态菜单）"
```

---

## Task 10: 前端 — App 入口 + 登录页

**Files:**
- Create: `frontend/src/pages/login/index.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: 创建登录页**

```typescript
// frontend/src/pages/login/index.tsx
import { useState } from 'react';
import { Button, Card, Form, Input, message, Typography } from 'antd';
import { LockOutlined, MailOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/auth';

const { Title } = Typography;

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.email, values.password);
      message.success('登录成功');
      navigate('/');
    } catch {
      message.error('用户名或密码错误');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', justifyContent: 'center',
      alignItems: 'center', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <Card style={{ width: 400, borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.15)' }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 32 }}>慢病管理系统</Title>
        <Form onFinish={onFinish} size="large">
          <Form.Item name="email" rules={[{ required: true, message: '请输入邮箱' }]}>
            <Input prefix={<MailOutlined />} placeholder="邮箱" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>登录</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: 创建 App.tsx**

```typescript
// frontend/src/App.tsx
import { useMemo, Suspense, lazy } from 'react';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useAuthStore } from '@/stores/auth';
import { generateRoutes } from '@/router/generateRoutes';
import AuthRoute from '@/router/AuthRoute';
import PageLoading from '@/components/PageLoading';

const LoginPage = lazy(() => import('@/pages/login/index'));
const AdminLayout = lazy(() => import('@/layouts/AdminLayout'));
const NotFound = lazy(() => import('@/pages/404'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5 * 60 * 1000, retry: 1, refetchOnWindowFocus: false },
  },
});

function AppRouter() {
  const menus = useAuthStore((s) => s.menus);

  const router = useMemo(() => {
    const dynamicRoutes = generateRoutes(menus);
    return createBrowserRouter([
      {
        path: '/login',
        element: <Suspense fallback={<PageLoading />}><LoginPage /></Suspense>,
      },
      {
        path: '/',
        element: <AuthRoute />,
        children: [
          {
            element: <Suspense fallback={<PageLoading />}><AdminLayout /></Suspense>,
            children: [
              { index: true, element: <Navigate to="/dashboard" replace /> },
              ...dynamicRoutes,
            ],
          },
        ],
      },
      { path: '*', element: <Suspense fallback={<PageLoading />}><NotFound /></Suspense> },
    ]);
  }, [menus]);

  return <RouterProvider router={router} />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN}>
        <AppRouter />
      </ConfigProvider>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 3: 更新 main.tsx**

```typescript
// frontend/src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 4: 验证登录流程**

```bash
cd frontend
npm run dev
```

确保后端已启动，访问 `http://localhost:5173`，应自动跳转到 `/login`。

- [ ] **Step 5: 提交**

```bash
cd frontend
git add src/pages/login/ src/App.tsx src/main.tsx
git commit -m "feat(frontend): 登录页 + App入口 + 路由组装"
```

---

## Task 11: 前端 — 仪表盘页面

**Files:**
- Create: `frontend/src/api/dashboard.ts`
- Create: `frontend/src/pages/dashboard/index.tsx`

- [ ] **Step 1: 创建仪表盘 API**

```typescript
// frontend/src/api/dashboard.ts
import { apiClient } from './client';

export interface DashboardStats {
  total_organizations: number;
  total_users: number;
  total_patients: number;
  total_conversations: number;
  active_users_24h: number;
  total_tokens_used: number;
  recent_failed_docs: number;
  token_usage_trend: { date: string; tokens: number }[];
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiClient.get('dashboard/stats').json<DashboardStats>();
}
```

- [ ] **Step 2: 创建仪表盘页面**

```typescript
// frontend/src/pages/dashboard/index.tsx
import { Card, Col, Row, Statistic, Spin, Typography } from 'antd';
import {
  TeamOutlined, UserOutlined, HeartOutlined,
  MessageOutlined, ThunderboltOutlined, CloudOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Line } from '@ant-design/charts';
import { getDashboardStats } from '@/api/dashboard';

const { Title } = Typography;

const statCards = [
  { key: 'total_organizations', title: '机构总数', icon: <TeamOutlined />, color: '#1677ff' },
  { key: 'total_users', title: '用户总数', icon: <UserOutlined />, color: '#52c41a' },
  { key: 'total_patients', title: '患者总数', icon: <HeartOutlined />, color: '#eb2f96' },
  { key: 'total_conversations', title: '对话总数', icon: <MessageOutlined />, color: '#722ed1' },
  { key: 'active_users_24h', title: '24h活跃', icon: <ThunderboltOutlined />, color: '#fa8c16' },
  { key: 'total_tokens_used', title: 'Token消耗', icon: <CloudOutlined />, color: '#13c2c2' },
  { key: 'recent_failed_docs', title: '失败文档', icon: <WarningOutlined />, color: '#f5222d' },
] as const;

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
  });

  if (isLoading || !data) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  const lineConfig = {
    data: data.token_usage_trend ?? [],
    xField: 'date',
    yField: 'tokens',
    smooth: true,
    point: { size: 3 },
    color: '#1677ff',
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>控制台</Title>
      <Row gutter={[16, 16]}>
        {statCards.map((card) => (
          <Col xs={24} sm={12} md={8} lg={6} key={card.key}>
            <Card hoverable>
              <Statistic
                title={card.title}
                value={(data as any)[card.key] ?? 0}
                prefix={card.icon}
                valueStyle={{ color: card.color }}
              />
            </Card>
          </Col>
        ))}
      </Row>
      <Card title="Token 用量趋势（近7天）" style={{ marginTop: 24 }}>
        <Line {...lineConfig} />
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: 提交**

```bash
cd frontend
git add src/api/dashboard.ts src/pages/dashboard/
git commit -m "feat(frontend): 仪表盘页面（统计卡片 + Token趋势图）"
```

---

## Task 12: 前端 — 患者管理（列表 + 详情 + 健康趋势图）

**Files:**
- Create: `frontend/src/api/patients.ts`
- Create: `frontend/src/api/health-metrics.ts`
- Create: `frontend/src/pages/patients/index.tsx`
- Create: `frontend/src/pages/patients/[id].tsx`
- Create: `frontend/src/pages/patients/components/HealthTrendChart.tsx`
- Create: `frontend/src/pages/patients/components/SuggestionList.tsx`

- [ ] **Step 1: 创建患者 API**

```typescript
// frontend/src/api/patients.ts
import { apiClient } from './client';
import type { PatientProfile } from '@/types/patient';

export async function getPatients(params?: {
  skip?: number; limit?: number; search?: string;
}): Promise<PatientProfile[]> {
  return apiClient.get('patients', { searchParams: params ?? {} }).json<PatientProfile[]>();
}

export async function getPatientById(id: string): Promise<PatientProfile> {
  return apiClient.get(`patients/${id}`).json<PatientProfile>();
}

export async function deletePatient(id: string): Promise<void> {
  await apiClient.delete(`patients/${id}`);
}
```

- [ ] **Step 2: 创建健康指标 API**

```typescript
// frontend/src/api/health-metrics.ts
import { apiClient } from './client';
import type { HealthMetric } from '@/types/patient';

export async function getPatientTrend(
  patientId: string,
  metricType: string,
  days: number = 30,
): Promise<HealthMetric[]> {
  return apiClient
    .get(`health-metrics/patients/${patientId}/trend`, {
      searchParams: { metric_type: metricType, days },
    })
    .json<HealthMetric[]>();
}
```

- [ ] **Step 3: 创建患者列表页**

```typescript
// frontend/src/pages/patients/index.tsx
import { useNavigate } from 'react-router-dom';
import { ProTable, type ProColumns } from '@ant-design/pro-components';
import { Button, Popconfirm, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getPatients, deletePatient } from '@/api/patients';
import { usePermission } from '@/hooks/usePermission';
import type { PatientProfile } from '@/types/patient';

export default function PatientListPage() {
  const navigate = useNavigate();
  const { hasPermission } = usePermission();

  const handleDelete = async (id: string) => {
    await deletePatient(id);
    message.success('删除成功');
  };

  const columns: ProColumns<PatientProfile>[] = [
    { title: '姓名', dataIndex: 'real_name', ellipsis: true },
    { title: '性别', dataIndex: 'gender', width: 80,
      valueEnum: { male: '男', female: '女', other: '其他' } },
    { title: '出生日期', dataIndex: 'birth_date', valueType: 'date', width: 120 },
    { title: '创建时间', dataIndex: 'created_at', valueType: 'dateTime', width: 180,
      sorter: true, hideInSearch: true },
    {
      title: '操作', width: 150, valueType: 'option',
      render: (_, record) => [
        <a key="view" onClick={() => navigate(`/patients/${record.id}`)}>详情</a>,
        hasPermission('patient:delete') && (
          <Popconfirm key="del" title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: '#f5222d' }}>删除</a>
          </Popconfirm>
        ),
      ],
    },
  ];

  return (
    <ProTable<PatientProfile>
      headerTitle="患者列表"
      rowKey="id"
      columns={columns}
      request={async (params) => {
        const data = await getPatients({
          skip: ((params.current ?? 1) - 1) * (params.pageSize ?? 20),
          limit: params.pageSize ?? 20,
          search: params.real_name,
        });
        return { data, success: true };
      }}
      toolBarRender={() => [
        hasPermission('patient:create') && (
          <Button key="add" type="primary" icon={<PlusOutlined />}>新建患者</Button>
        ),
      ]}
      pagination={{ defaultPageSize: 20 }}
      search={{ labelWidth: 'auto' }}
    />
  );
}
```

- [ ] **Step 4: 创建健康趋势图组件**

```typescript
// frontend/src/pages/patients/components/HealthTrendChart.tsx
import { useState } from 'react';
import { Card, Select, Space } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { Line } from '@ant-design/charts';
import { getPatientTrend } from '@/api/health-metrics';

const METRIC_OPTIONS = [
  { label: '血压', value: 'blood_pressure' },
  { label: '血糖', value: 'blood_sugar' },
  { label: '体重', value: 'weight' },
  { label: '心率', value: 'heart_rate' },
  { label: 'BMI', value: 'bmi' },
  { label: '血氧', value: 'spo2' },
];

const DAY_OPTIONS = [
  { label: '近7天', value: 7 },
  { label: '近30天', value: 30 },
  { label: '近90天', value: 90 },
];

export default function HealthTrendChart({ patientId }: { patientId: string }) {
  const [metricType, setMetricType] = useState('blood_pressure');
  const [days, setDays] = useState(30);

  const { data = [], isLoading } = useQuery({
    queryKey: ['patient-trend', patientId, metricType, days],
    queryFn: () => getPatientTrend(patientId, metricType, days),
  });

  // 血压需要双线（收缩压 + 舒张压）
  const isBloodPressure = metricType === 'blood_pressure';
  const chartData = isBloodPressure
    ? data.flatMap((d) => [
        { date: d.measured_at, value: d.value, type: '收缩压' },
        { date: d.measured_at, value: d.value_secondary ?? 0, type: '舒张压' },
      ])
    : data.map((d) => ({ date: d.measured_at, value: d.value, type: metricType }));

  return (
    <Card
      title="健康指标趋势"
      extra={
        <Space>
          <Select value={metricType} onChange={setMetricType}
            options={METRIC_OPTIONS} style={{ width: 100 }} />
          <Select value={days} onChange={setDays}
            options={DAY_OPTIONS} style={{ width: 100 }} />
        </Space>
      }
    >
      <Line
        data={chartData}
        loading={isLoading}
        xField="date"
        yField="value"
        seriesField={isBloodPressure ? 'type' : undefined}
        smooth
        point={{ size: 3 }}
        height={300}
      />
    </Card>
  );
}
```

- [ ] **Step 5: 创建管理建议列表组件**

```typescript
// frontend/src/pages/patients/components/SuggestionList.tsx
import { Card, List, Tag, Empty } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { ManagementSuggestion } from '@/types/patient';

const TYPE_COLOR: Record<string, string> = {
  clinical: 'red',
  lifestyle: 'green',
  general: 'blue',
};

const TYPE_LABEL: Record<string, string> = {
  clinical: '临床建议',
  lifestyle: '生活方式',
  general: '综合建议',
};

export default function SuggestionList({ patientId }: { patientId: string }) {
  const { data = [], isLoading } = useQuery({
    queryKey: ['patient-suggestions', patientId],
    queryFn: () =>
      apiClient
        .get(`managers/patients/${patientId}/suggestions`)
        .json<ManagementSuggestion[]>(),
  });

  return (
    <Card title="管理建议">
      {data.length === 0 && !isLoading ? (
        <Empty description="暂无管理建议" />
      ) : (
        <List
          loading={isLoading}
          dataSource={data}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <span>
                    <Tag color={TYPE_COLOR[item.suggestion_type] ?? 'default'}>
                      {TYPE_LABEL[item.suggestion_type] ?? item.suggestion_type}
                    </Tag>
                    {item.created_at}
                  </span>
                }
                description={item.content}
              />
            </List.Item>
          )}
        />
      )}
    </Card>
  );
}
```

- [ ] **Step 6: 创建患者详情页**

```typescript
// frontend/src/pages/patients/[id].tsx
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Button, Card, Descriptions, Spin, Tabs, Typography } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { getPatientById } from '@/api/patients';
import HealthTrendChart from './components/HealthTrendChart';
import SuggestionList from './components/SuggestionList';

const { Title } = Typography;

export default function PatientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: patient, isLoading } = useQuery({
    queryKey: ['patient', id],
    queryFn: () => getPatientById(id!),
    enabled: !!id,
  });

  if (isLoading || !patient) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  return (
    <div style={{ padding: 24 }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}
        style={{ marginBottom: 16 }}>返回</Button>
      <Title level={4}>{patient.real_name || '未命名'} 的患者档案</Title>

      <Tabs
        defaultActiveKey="info"
        items={[
          {
            key: 'info',
            label: '基本信息',
            children: (
              <Card>
                <Descriptions column={2}>
                  <Descriptions.Item label="姓名">{patient.real_name}</Descriptions.Item>
                  <Descriptions.Item label="性别">{patient.gender}</Descriptions.Item>
                  <Descriptions.Item label="出生日期">{patient.birth_date}</Descriptions.Item>
                  <Descriptions.Item label="创建时间">{patient.created_at}</Descriptions.Item>
                  <Descriptions.Item label="病史" span={2}>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                      {patient.medical_history
                        ? JSON.stringify(patient.medical_history, null, 2)
                        : '无'}
                    </pre>
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            ),
          },
          {
            key: 'metrics',
            label: '健康指标',
            children: <HealthTrendChart patientId={id!} />,
          },
          {
            key: 'suggestions',
            label: '管理建议',
            children: <SuggestionList patientId={id!} />,
          },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 7: 提交**

```bash
cd frontend
git add src/api/patients.ts src/api/health-metrics.ts src/pages/patients/
git commit -m "feat(frontend): 患者管理模块（列表+详情+健康趋势图+管理建议）"
```

---

## 自检清单

| # | 检查项 | 结果 |
|---|--------|------|
| 1 | 设计文档中的 menus 表结构是否全部覆盖 | ✅ 全部 15 个字段 |
| 2 | `/auth/menu-tree` 重写是否从 menus 表读取 | ✅ Task 4 |
| 3 | 管理端健康指标趋势接口是否补充 | ✅ Task 4 |
| 4 | 前端所有 ID 类型是否为 string | ✅ types/*.ts |
| 5 | ky 客户端是否自动注入 Token + X-Organization-ID | ✅ Task 6 |
| 6 | 401 是否自动跳转登录页 | ✅ afterResponse hook |
| 7 | 动态路由是否从后端菜单生成 | ✅ generateRoutes |
| 8 | 路由模块注册表 code 是否与种子数据 code 一致 | ✅ dashboard / patient-list |
| 9 | 血压双线图是否特殊处理 | ✅ HealthTrendChart |
| 10 | 无占位符/TBD/TODO | ✅ 已扫描 |
| 11 | 类型名一致性（MenuItem / PatientProfile / HealthMetric） | ✅ 全文一致 |
