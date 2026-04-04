# 设计规格：租户与组织拆分重构

> 日期：2026-04-04
> 状态：已确认
> 范围：后端完整重构 + 前端最小适配

## 1. 背景与动机

当前系统将"租户"和"组织"合并在 `organizations` 表中，导致：
- `organizations` 同时承担计费隔离和部门层级两个职责，概念混淆
- 子组织有独立的 `plan_type` 和 `quota`，但语义不清（子公司 vs 内部部门）
- 超管穿透逻辑在"跨租户"和"跨部门"之间界限模糊

本次重构拆分为两个独立实体：
- **`tenants`**：签约客户，计费主体，数据隔离的绝对边界
- **`organizations`**：租户内部的部门/科室，支持树形层级，部门间数据隔离

## 2. 核心设计决策

| 决策 | 选择 | 依据 |
|------|------|------|
| 重构范围 | 完整重构（一次到位） | 渐进方案会长期留两套逻辑 |
| Tenant 定位 | 完整客户实体（含计费+客户信息） | 表结构一次设计对，UI 后续补 |
| 业务表字段 | `tenant_id` + `org_id` 双字段 | 部门间也需要数据隔离 |
| 组织树层级 | 仅在 `organizations` 表（部门层级） | 集团跨租户管理是后期需求 |
| 前端上下文 | JWT 内嵌 `tenant_id` + Header 传 `X-Organization-ID` | 业内成熟做法，零额外查询 |
| RLS 策略 | 仅在 `tenant_id` 上建 RLS | 部门隔离是可被管理员覆盖的业务规则，放应用层 |
| 迁移策略 | 删除全部旧迁移，从零重建 | 历史迁移存在类型冲突和分叉 |

## 3. 数据模型

### 3.1 新增 `tenants` 表

```python
class Tenant(Base, IDMixin, TimestampMixin):
    __tablename__ = "tenants"

    # 基本信息
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active"
    )  # active / trial / suspended / archived
    plan_type: Mapped[str] = mapped_column(
        String(50), default="free", server_default="free"
    )  # free / pro / enterprise

    # 配额
    quota_tokens_limit: Mapped[int] = mapped_column(
        BigInteger, default=1000000, server_default="1000000"
    )
    quota_tokens_used: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0"
    )
    max_members: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_patients: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 客户信息（预留，暂不做前端管理页面）
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    org_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # hospital / clinic / community_health
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    trial_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    organizations: Mapped[list["Organization"]] = relationship(back_populates="tenant")
```

### 3.2 修改 `organizations` 表

```python
class Organization(Base, IDMixin, TimestampMixin):
    __tablename__ = "organizations"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active"
    )  # active / inactive / archived
    sort: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dept_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # clinical / administrative / support

    # 删除的字段：plan_type, quota_tokens_limit, quota_tokens_used

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="organizations")
    parent: Mapped["Organization | None"] = relationship(
        remote_side="Organization.id", back_populates="children"
    )
    children: Mapped[list["Organization"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_org_tenant_code"),
        Index("idx_org_tenant_parent_sort", "tenant_id", "parent_id", "sort"),
    )
```

### 3.3 业务表变更

所有原来只有 `org_id` 的业务表新增 `tenant_id` 列（NOT NULL，FK → tenants.id），`org_id` 保留表示部门归属。

受影响表清单：
- `organization_users`：+`tenant_id`
- `organization_user_roles`：+`tenant_id`
- `patient_profiles`：+`tenant_id`
- `health_metrics`：+`tenant_id`
- `manager_profiles`：+`tenant_id`
- `patient_manager_assignments`：+`tenant_id`，改主键为 `(tenant_id, org_id, manager_id, patient_id)`
- `management_suggestions`：+`tenant_id`
- `knowledge_bases`：+`tenant_id`
- `documents`：+`tenant_id`
- `chunks`：+`tenant_id`
- `conversations`：+`tenant_id`
- `messages`：+`tenant_id`
- `usage_logs`：+`tenant_id`
- `api_keys`：+`tenant_id`
- `audit_logs`：+`tenant_id`（改为 NOT NULL）
- `menus`：+`tenant_id`（可空，系统菜单 = NULL）
- `roles`：+`tenant_id`（可空，系统角色 = NULL，替代原 `org_id`）

### 3.4 不变的表

- `users`、`password_reset_tokens`：全局共享
- `permissions`、`rbac_resources`、`rbac_actions`：系统级静态数据
- `patient_family_links`：跨租户关系，无 tenant_id
- `system_settings`：全局

## 4. 认证与上下文流程

### 4.1 JWT Payload

```json
{
  "sub": "<user_id>",
  "tenant_id": "<tenant_id>",
  "exp": "..."
}
```

### 4.2 登录流程

```
POST /auth/login {email, password}
  → 验证密码
  → 查用户所属租户列表（通过 organization_users → organizations → tenants）
  → 0 个租户 → 400 错误
  → 1 个租户 → 自动选中，返回含 tenant_id 的 JWT
  → N 个租户 → 返回租户列表 + selection_token，等待选择
```

单租户响应：
```json
{
  "access_token": "eyJ...",
  "tenant": {"id": 123, "name": "北京协和医院"},
  "require_tenant_selection": false
}
```

多租户响应：
```json
{
  "access_token": null,
  "tenants": [{"id": 123, "name": "..."}, {"id": 456, "name": "..."}],
  "require_tenant_selection": true,
  "selection_token": "短期临时token"
}
```

### 4.3 新增端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `POST /auth/select-tenant` | POST | 登录后选择租户，body: `{tenant_id}`，需要 `selection_token` |
| `POST /auth/switch-tenant` | POST | 已登录切换租户，body: `{tenant_id}`，需要有效 JWT |
| `GET /auth/tenants` | GET | 获取当前用户可用租户列表 |

### 4.4 依赖注入重构

`get_current_org_user()` 拆分为：

```python
# 1. 从 JWT 读取租户 ID（零查询）
async def get_current_tenant(token) -> int:
    return token.payload["tenant_id"]

# 2. 注入 RLS 上下文
async def inject_rls_context(tenant_id, db):
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(tenant_id)}
    )

# 3. 获取部门上下文（可选）
async def get_current_org_user(request, tenant_id, db) -> OrganizationUser | None:
    org_id = request.headers.get("X-Organization-ID")
    if org_id:
        org = await db.get(Organization, int(org_id))
        if not org or org.tenant_id != tenant_id:
            raise HTTPException(403, "部门不属于当前租户")
        # 查 OrganizationUser 记录和角色
        ...
    return None  # 管理员不需要指定部门
```

### 4.5 端点注入模式

```python
@router.get("/patients")
async def list_patients(
    tenant_id: int = Depends(get_current_tenant),
    org_user: OrganizationUser | None = Depends(get_current_org_user),
    db = Depends(get_db),
):
    stmt = select(PatientProfile).where(PatientProfile.tenant_id == tenant_id)
    if org_user and not is_tenant_admin(org_user):
        stmt = stmt.where(PatientProfile.org_id == org_user.org_id)
    ...
```

## 5. RLS 策略

### 5.1 策略模板

```sql
CREATE POLICY {table}_tenant_isolation ON {table}
    USING (tenant_id = current_setting('app.current_tenant_id', true)::bigint);
```

### 5.2 覆盖范围

16 张表启用 RLS，全部基于 `tenant_id`：
- organizations, organization_users
- patient_profiles（含家属穿透子查询）
- health_metrics, manager_profiles, patient_manager_assignments
- management_suggestions（含家属穿透子查询）
- knowledge_bases, documents, chunks
- conversations, messages
- usage_logs, api_keys, audit_logs
- roles（`tenant_id = X OR tenant_id IS NULL` 支持系统角色全局可见）

不需要 RLS 的表：users, password_reset_tokens, permissions, rbac_resources, rbac_actions, patient_family_links, system_settings, menus

### 5.3 家属穿透

```sql
CREATE POLICY patient_profiles_tenant_isolation ON patient_profiles
    USING (
        tenant_id = current_setting('app.current_tenant_id', true)::bigint
        OR id IN (
            SELECT patient_id FROM patient_family_links
            WHERE family_user_id = current_setting('app.current_user_id', true)::bigint
        )
    );
```

## 6. 迁移策略

### 6.1 方案：全量重建

1. 删除 `alembic/versions/` 下所有文件
2. DROP 现有数据库（开发环境）
3. 从新模型生成初始迁移：`alembic revision --autogenerate -m "initial_schema"`
4. 在迁移中手动追加：RLS 策略、pgvector 扩展、自定义索引
5. `alembic upgrade head`
6. 运行新种子数据

### 6.2 索引策略

```sql
-- 所有 tenant_id 列需要单列索引
CREATE INDEX idx_{table}_tenant_id ON {table}(tenant_id);

-- 高频查询复合索引
CREATE INDEX idx_health_metrics_tenant_org ON health_metrics(tenant_id, org_id, patient_id);
CREATE INDEX idx_patient_profiles_tenant_org ON patient_profiles(tenant_id, org_id);
CREATE INDEX idx_conversations_tenant_user ON conversations(tenant_id, user_id);
CREATE INDEX idx_documents_tenant_kb ON documents(tenant_id, kb_id);
CREATE INDEX idx_org_tenant_parent ON organizations(tenant_id, parent_id);
```

## 7. 种子数据

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

# 流程：Tenant → Organization → User → OrganizationUser → Role 绑定
```

## 8. 前端适配（最小范围）

- `stores/auth.ts`：存储 `tenant_id`
- `api/auth.ts`：新增 `selectTenant()`、`switchTenant()`、`getTenants()`
- 登录页：处理 `require_tenant_selection` 响应
- `api/client.ts`：无变化（`X-Organization-ID` 保持）

## 9. 不在本次范围

- 租户管理前端页面（CRUD）
- 集团跨租户管理（`tenants.parent_tenant_id`）
- 租户自定义菜单功能
- SMTP 邮件通知

## 10. 文件变更清单

| 文件 | 操作 |
|------|------|
| `models/tenant.py` | 新建 |
| `models/organization.py` | 改：加 tenant_id，删配额字段，加新字段 |
| `models/patient.py` | 改：加 tenant_id |
| `models/health_metric.py` | 改：加 tenant_id |
| `models/manager.py` | 改：3 表加 tenant_id |
| `models/knowledge.py` | 改：3 表加 tenant_id |
| `models/chat.py` | 改：3 表加 tenant_id |
| `models/api_key.py` | 改：加 tenant_id |
| `models/audit.py` | 改：tenant_id NOT NULL |
| `models/menu.py` | 改：加 tenant_id 可空 |
| `models/rbac.py` | 改：tenant_id 替代 org_id |
| `models/__init__.py` | 改：导出 Tenant |
| `core/security.py` | 改：JWT 加 tenant_id |
| `api/deps.py` | 重写：拆分三个依赖 |
| `api/endpoints/auth.py` | 改：登录流程 + 新端点 |
| `api/endpoints/*.py` | 改：所有端点适配新依赖 |
| `services/quota.py` | 改：从 Tenant 读配额 |
| `services/rbac.py` | 改：角色查询改 tenant_id |
| `db/seed_data.py` | 改：先建 Tenant 后建 Org |
| `alembic/versions/` | 删除全部，重新生成 |
