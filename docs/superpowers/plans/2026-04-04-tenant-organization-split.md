# 租户与组织拆分重构 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 拆分 `organizations` 表为 `tenants`（租户/隔离边界）+ `organizations`（部门/科室），实现双层数据隔离

**Architecture:** 新增 `tenants` 表作为计费主体和 RLS 隔离边界，`organizations` 瘦身为租户内的部门实体。所有业务表新增 `tenant_id` 列，RLS 策略统一基于 `tenant_id`。JWT payload 内嵌 `tenant_id`，`X-Organization-ID` 请求头做部门级过滤。

**Tech Stack:** FastAPI, SQLAlchemy 2.x Async, PostgreSQL + pgvector, Alembic, JWT (PyJWT)

**Spec:** [2026-04-04-tenant-organization-split-design.md](file:///d:/codes/chronic-disease-management/docs/superpowers/specs/2026-04-04-tenant-organization-split-design.md)

---

## Task 1: 清理旧迁移 + 创建 Tenant 模型

**Files:**
- Delete: `backend/alembic/versions/*.py`
- Create: `backend/app/db/models/tenant.py`
- Modify: `backend/app/db/models/__init__.py`

- [ ] **Step 1: 删除所有旧迁移文件**

```powershell
Remove-Item d:\codes\chronic-disease-management\backend\alembic\versions\*.py
```

- [ ] **Step 2: 创建 Tenant 模型**

创建 `backend/app/db/models/tenant.py`：

```python
"""租户模型：SaaS 多租户的计费主体与数据隔离边界"""
from datetime import datetime

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin


class Tenant(Base, IDMixin, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active",
        comment="active / trial / suspended / archived",
    )
    plan_type: Mapped[str] = mapped_column(
        String(50), default="free", server_default="free",
        comment="free / pro / enterprise",
    )

    quota_tokens_limit: Mapped[int] = mapped_column(
        BigInteger, default=1_000_000, server_default="1000000",
    )
    quota_tokens_used: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0",
    )
    max_members: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_patients: Mapped[int | None] = mapped_column(Integer, nullable=True)

    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    org_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="hospital / clinic / community_health",
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    trial_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    organizations: Mapped[list["Organization"]] = relationship(
        "Organization", back_populates="tenant",
    )
```

- [ ] **Step 3: 更新 `__init__.py` 导出 Tenant**

修改 `backend/app/db/models/__init__.py`，在 `from .base import Base` 之后添加：

```python
from .tenant import Tenant
```

并在 `__all__` 列表中添加 `"Tenant"`。

- [ ] **Step 4: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend/app/db/models/tenant.py backend/app/db/models/__init__.py
git commit -m "feat: add Tenant model and delete old migrations"
```

---

## Task 2: 重构 Organization 模型

**Files:**
- Modify: `backend/app/db/models/organization.py`

- [ ] **Step 1: 重写 Organization 类**

将 `backend/app/db/models/organization.py` 中的 `Organization` 类（第 13-40 行）替换为：

```python
class Organization(Base, IDMixin, TimestampMixin):
    __tablename__ = "organizations"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active",
        comment="active / inactive / archived",
    )
    sort: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dept_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="clinical / administrative / support",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="organizations")
    parent: Mapped["Organization | None"] = relationship(
        remote_side="Organization.id", back_populates="children",
    )
    children: Mapped[list["Organization"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan",
    )
    users: Mapped[list["OrganizationUser"]] = relationship(
        back_populates="organization",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_org_tenant_code"),
        Index("idx_org_tenant_parent_sort", "tenant_id", "parent_id", "sort"),
    )
```

文件顶部导入更新为：

```python
from sqlalchemy import String, ForeignKey, BigInteger, ForeignKeyConstraint, Integer, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING
from .base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .patient import PatientProfile
    from .rbac import Role
    from .tenant import Tenant
```

- [ ] **Step 2: OrganizationUser 加 tenant_id**

将 `OrganizationUser` 类（第 43-60 行）替换为：

```python
class OrganizationUser(Base, TimestampMixin):
    __tablename__ = "organization_users"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True,
    )
    user_type: Mapped[str] = mapped_column(
        String(20), default="staff", server_default="staff",
    )

    organization: Mapped["Organization"] = relationship(back_populates="users")
    user: Mapped["User"] = relationship(back_populates="organizations")
    rbac_roles: Mapped[list["Role"]] = relationship(secondary="organization_user_roles")
```

- [ ] **Step 3: OrganizationUserRole 加 tenant_id**

将 `OrganizationUserRole` 类（第 63-78 行）替换为：

```python
class OrganizationUserRole(Base, TimestampMixin):
    __tablename__ = "organization_user_roles"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    )
    org_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "user_id"],
            ["organization_users.org_id", "organization_users.user_id"],
            ondelete="CASCADE",
        ),
    )
```

- [ ] **Step 4: OrganizationInvitation 加 tenant_id**

在 `OrganizationInvitation` 类（第 81 行起）的 `org_id` 字段之前添加：

```python
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    )
```

- [ ] **Step 5: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend/app/db/models/organization.py
git commit -m "feat: refactor Organization model with tenant_id, add dept fields"
```

---

## Task 3: 业务模型加 tenant_id

**Files:**
- Modify: `backend/app/db/models/patient.py`
- Modify: `backend/app/db/models/health_metric.py`
- Modify: `backend/app/db/models/manager.py`
- Modify: `backend/app/db/models/knowledge.py`
- Modify: `backend/app/db/models/chat.py`
- Modify: `backend/app/db/models/api_key.py`
- Modify: `backend/app/db/models/audit.py`
- Modify: `backend/app/db/models/menu.py`
- Modify: `backend/app/db/models/rbac.py`

- [ ] **Step 1: patient.py**

在 `PatientProfile` 的 `user_id` 之前添加：

```python
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    )
```

唯一约束改为 `UniqueConstraint("tenant_id", "org_id", "user_id", name="uq_patient_profiles_tenant_org_user")`。

- [ ] **Step 2: health_metric.py**

在 `patient_id` 之前添加 `tenant_id` 字段。添加复合索引 `Index("idx_health_metrics_tenant_org", "tenant_id", "org_id", "patient_id")`。

- [ ] **Step 3: manager.py — 三张表**

`ManagerProfile`：在 `user_id` 之前加 `tenant_id`。

`PatientManagerAssignment`：完整替换为四字段复合主键 `(tenant_id, org_id, manager_id, patient_id)`：

```python
class PatientManagerAssignment(Base, TimestampMixin):
    __tablename__ = "patient_manager_assignments"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True,
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True,
    )
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), primary_key=True)
    assignment_role: Mapped[str] = mapped_column(String(50), default="main")

    manager: Mapped["User"] = relationship()
    patient: Mapped["PatientProfile"] = relationship()
```

`ManagementSuggestion`：在 `org_id` 之前加 `tenant_id`。索引改为 `Index('idx_tenant_patient_suggest', 'tenant_id', 'org_id', 'patient_id', 'created_at')`。

- [ ] **Step 4: knowledge.py — 三张表**

`KnowledgeBase`、`Document`、`Chunk`：每张表在 `org_id` 之前加 `tenant_id`。`Chunk.__table_args__` 索引改为 `Index('idx_tenant_kb_chunk', 'tenant_id', 'kb_id')`。

- [ ] **Step 5: chat.py — 三张表**

`Conversation`、`Message`、`UsageLog`：每张表加 `tenant_id`。

- [ ] **Step 6: api_key.py**

在 `org_id` 之前加 `tenant_id`。

- [ ] **Step 7: audit.py**

替换为：

```python
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    )
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), index=True, nullable=True,
    )
```

- [ ] **Step 8: menu.py**

在 `parent_id` 之后添加 `tenant_id`（可空）：

```python
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True,
    )
```

- [ ] **Step 9: rbac.py — Role 和 RoleConstraint**

`Role`：将 `org_id` 改为 `tenant_id`：

```python
    tenant_id: Mapped[int | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=True,
    )
```

唯一约束改为 `UniqueConstraint('tenant_id', 'code', name='_tenant_role_code_uc')`。

`RoleConstraint`：同样将 `org_id` 改为 `tenant_id`。

- [ ] **Step 10: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend/app/db/models/
git commit -m "feat: add tenant_id to all business models"
```

---

## Task 4: JWT 安全模块重构

**Files:**
- Modify: `backend/app/core/security.py`

- [ ] **Step 1: 修改 create_access_token**

替换 `create_access_token` 函数（第 20-28 行）：

```python
def create_access_token(
    subject: str | int,
    tenant_id: int | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict = {"exp": expire, "sub": str(subject)}
    if tenant_id is not None:
        to_encode["tenant_id"] = str(tenant_id)
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt
```

- [ ] **Step 2: 新增 create_selection_token**

在文件末尾添加：

```python
def create_selection_token(user_id: str | int) -> str:
    """创建短期临时 token，仅用于 select-tenant 端点"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    to_encode = {"exp": expire, "sub": str(user_id), "purpose": "tenant_selection"}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
```

- [ ] **Step 3: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend/app/core/security.py
git commit -m "feat: JWT payload includes tenant_id, add selection token"
```

---

## Task 5: 依赖注入层重写

**Files:**
- Modify: `backend/app/api/deps.py`

- [ ] **Step 1: 完整重写 deps.py**

将 `backend/app/api/deps.py` 的全部内容替换为分层依赖架构。核心结构：

1. `get_current_user(token, db)` — 从 JWT 解析用户
2. `get_current_tenant_id(token)` — 从 JWT 读取 tenant_id（零查询）
3. `inject_rls_context(tenant_id, user, db)` — 注入 `app.current_tenant_id` 到 PostgreSQL 会话
4. `get_current_org_user(request, tenant_id, user, db)` — 从 Header 读取部门上下文 + 管理员穿透
5. `check_permission(code)` — RBAC 权限校验

关键逻辑：
- `get_current_org_user` 校验 `org.tenant_id == tenant_id` 防止跨租户
- 未指定部门时取用户在该租户下的第一个部门
- 管理员（admin/owner）可穿透访问同租户内其他部门

- [ ] **Step 2: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend/app/api/deps.py
git commit -m "feat: rewrite deps.py with layered tenant/org context injection"
```

---

## Task 6: 认证端点适配

**Files:**
- Modify: `backend/app/api/endpoints/auth.py`

- [ ] **Step 1: 重写登录端点**

查用户所属租户列表，单租户自动签发含 `tenant_id` 的 JWT，多租户返回选择列表 + `selection_token`。

- [ ] **Step 2: 新增 select-tenant 端点**

验证 `selection_token` 有效性和 `purpose == "tenant_selection"`，校验用户属于目标租户后签发正式 JWT。

- [ ] **Step 3: 新增 switch-tenant 端点**

已登录用户切换租户，校验归属后签发新 JWT。

- [ ] **Step 4: 新增 GET /auth/tenants 端点**

返回当前用户可用的租户列表。

- [ ] **Step 5: 重写 register 端点**

创建用户后先创建 Tenant，再创建 Organization。

- [ ] **Step 6: 更新 /me 和 menu-tree 端点**

返回 `tenant_id`，菜单查询改用 `tenant_id` 过滤。

- [ ] **Step 7: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend/app/api/endpoints/auth.py
git commit -m "feat: login flow with tenant selection, add switch/select tenant"
```

---

## Task 7: 服务层适配

**Files:**
- Modify: `backend/app/services/quota.py`
- Modify: `backend/app/services/rbac.py`

- [ ] **Step 1: quota.py — 配额从 Tenant 读取**

所有 `Organization.quota_*` 引用改为 `Tenant.quota_*`。Redis key 从 `quota:{org_id}` 改为 `quota:{tenant_id}`。

- [ ] **Step 2: rbac.py — 角色查询改用 tenant_id**

`Role.org_id` 条件改为 `Role.tenant_id`。

- [ ] **Step 3: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend/app/services/
git commit -m "feat: quota from Tenant, RBAC uses tenant_id"
```

---

## Task 8: 全部端点适配

**Files:**
- Modify: `backend/app/api/endpoints/*.py`（16 个文件）

通用修改模式：
- 依赖注入改为 `tenant_id = Depends(get_current_tenant_id)` + `org_user = Depends(get_current_org_user)`
- 查询加 `Model.tenant_id == tenant_id`
- 创建记录时注入 `tenant_id` 和 `org_id`
- 管理员视角省略 `org_id` 过滤

- [ ] **Step 1: patients.py, health_metrics.py**
- [ ] **Step 2: managers.py**（upsert 的 `index_elements` 改为四字段）
- [ ] **Step 3: knowledge_bases.py, documents.py**
- [ ] **Step 4: chat.py, conversations.py**
- [ ] **Step 5: organizations.py**（创建部门时需传 `tenant_id`）
- [ ] **Step 6: dashboard.py**（统计改为 `tenant_id` 聚合）
- [ ] **Step 7: api_keys.py, audit_logs.py, usage.py, settings.py, rbac.py, users.py, family.py, external_api.py**
- [ ] **Step 8: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend/app/api/endpoints/
git commit -m "feat: all endpoints adapted to tenant_id + org_id dual context"
```

---

## Task 9: 种子数据重写

**Files:**
- Modify: `backend/app/db/seed_data.py`

- [ ] **Step 1: 更新常量 — 新增 DEFAULT_TENANT**

```python
DEFAULT_TENANT = {
    "name": "默认租户",
    "slug": "default",
    "plan_type": "enterprise",
    "status": "active",
    "quota_tokens_limit": 1000000,
}

DEFAULT_ORG = {
    "name": "默认部门",
    "code": "DEFAULT",
    "status": "active",
    "sort": 0,
}
```

- [ ] **Step 2: 重写 seed_super_admin**

创建顺序改为：Tenant → Organization → User → OrganizationUser → OrganizationUserRole。所有关联记录加 `tenant_id`。

- [ ] **Step 3: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend/app/db/seed_data.py
git commit -m "feat: seed data creates Tenant before Organization"
```

---

## Task 10: 生成迁移 + RLS 策略

**Files:**
- Create: `backend/alembic/versions/` 新迁移文件

- [ ] **Step 1: 重建数据库**

```powershell
cd d:\codes\chronic-disease-management\backend
# 根据本地配置 DROP 并重建数据库
```

- [ ] **Step 2: 生成初始迁移**

```powershell
cd d:\codes\chronic-disease-management\backend
uv run alembic revision --autogenerate -m "initial_schema_with_tenants"
```

- [ ] **Step 3: 在迁移中追加 RLS 策略和 pgvector 扩展**

在生成的迁移 `upgrade()` 末尾手动追加 16 张表的 RLS 策略，包括 `patient_profiles` 和 `management_suggestions` 的家属穿透子查询，以及 `roles` 的系统角色全局可见策略。

- [ ] **Step 4: 执行迁移**

```powershell
cd d:\codes\chronic-disease-management\backend
uv run alembic upgrade head
```

- [ ] **Step 5: 运行种子数据**

```powershell
cd d:\codes\chronic-disease-management\backend
uv run python -m app.db.seed_data
```

- [ ] **Step 6: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend/alembic/
git commit -m "feat: initial migration with RLS on tenant_id"
```

---

## Task 11: 前端最小适配

**Files:**
- Modify: `frontend/apps/website/src/stores/auth.ts`
- Modify: `frontend/apps/website/src/api/auth.ts`
- Modify: `frontend/apps/website/src/pages/login/index.tsx`

- [ ] **Step 1: auth store 增加 tenant 状态**

添加 `tenantId`、`tenantName` 到 zustand state。

- [ ] **Step 2: auth API 新增租户接口**

添加 `selectTenant()`、`switchTenant()`、`getTenants()`。

- [ ] **Step 3: 登录页处理 tenant 选择**

如果 `require_tenant_selection === true`，显示租户选择弹窗。

- [ ] **Step 4: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add frontend/
git commit -m "feat: frontend handles tenant selection on login"
```

---

## Task 12: 更新项目文档

**Files:**
- Modify: `GEMINI.md`

- [ ] **Step 1: 更新数据模型和架构说明**

添加 Tenant 实体、双层隔离架构、JWT tenant_id 机制的描述。

- [ ] **Step 2: 更新开发约定**

新增租户相关开发规范。

- [ ] **Step 3: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add GEMINI.md
git commit -m "docs: update project guide for tenant-organization architecture"
```
