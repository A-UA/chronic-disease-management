# 递归组织架构与系统核心修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复后端导入错误与 Dashboard 逻辑故障，实现递归组织架构，并全面统一前后端雪花 ID 为字符串处理。

**Architecture:** 
1. 修正后端目录结构引用与 `deps.py` 缺失函数。
2. 数据库 `organizations` 表增加 `parent_id` 并利用 Recursive CTE 实现多级统计。
3. 全局拦截异常响应并使用 `SnowflakeJSONResponse`。
4. 前端 TS 类型全量替换。

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (PostgreSQL), UmiJS (React), TypeScript

---

### Task 1: 基础环境与测试路径修复 (P0)

**Files:**
- Modify: `backend/tests/api/test_admin_organizations.py`
- Modify: `backend/tests/api/test_chat.py`
- Modify: `backend/tests/test_main.py`
- Modify: `backend/tests/test_manager_workbench.py`
- Modify: `backend/app/api/deps.py`

- [ ] **Step 1: 补全 `get_current_active_user` 依赖项**
在 `backend/app/api/deps.py` 中增加：
```python
async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    # 暂不增加 active 字段检查，保持与现有 User 模型兼容，仅作别名修复阻塞
    return current_user
```

- [ ] **Step 2: 修正测试用例中的导入路径 (Organizations)**
修改 `backend/tests/api/test_admin_organizations.py`:
```python
# From: from app.api.endpoints.admin.organizations import router
# To:
from app.api.endpoints.organizations import router
```

- [ ] **Step 3: 修正测试用例中的导入路径 (Chat)**
修改 `backend/tests/api/test_chat.py`:
```python
# From: from app.api.endpoints.biz.chat import router
# To:
from app.api.endpoints.chat import router
```

- [ ] **Step 4: 运行测试收集，验证导入错误已消除**
Run: `cd backend && uv run python -m pytest --collect-only`
Expected: 能够成功列出测试用例，不再报 `ModuleNotFoundError`。

- [ ] **Step 5: Commit**
```bash
git add backend/app/api/deps.py backend/tests/
git commit -m "fix: resolve import errors and missing dependencies in tests"
```

---

### Task 2: 递归组织树数据库变更 (P1)

**Files:**
- Modify: `backend/app/db/models/organization.py`
- Create: `backend/alembic/versions/2026_04_01_add_recursive_org_and_fix_rls.py`

- [ ] **Step 1: 修改 Organization 模型**
在 `backend/app/db/models/organization.py` 中增加 `parent_id`:
```python
class Organization(Base, IDMixin, TimestampMixin):
    # ... 现有字段
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    
    # Relationships
    children: Mapped[list["Organization"]] = relationship(back_populates="parent")
    parent: Mapped["Organization | None"] = relationship(back_populates="children", remote_side="Organization.id")
```

- [ ] **Step 2: 创建迁移脚本并修正 RLS 健壮性**
Run: `cd backend && uv run alembic revision -m "add_recursive_org_and_fix_rls"`
在生成的脚本中实现：
1. `op.add_column('organizations', sa.Column('parent_id', sa.BigInteger(), nullable=True))`
2. 修正 RLS 策略，在所有 `current_setting` 中增加 `true` 参数。
```python
# 示例：
op.execute("DROP POLICY IF EXISTS documents_isolation_policy ON documents")
op.execute("CREATE POLICY documents_isolation_policy ON documents USING (org_id = current_setting('app.current_org_id', true)::bigint)")
```

- [ ] **Step 3: 执行迁移**
Run: `cd backend && uv run alembic upgrade head`

- [ ] **Step 4: Commit**
```bash
git add backend/app/db/models/organization.py backend/alembic/versions/
git commit -m "feat: add recursive parent_id to organizations and harden RLS policies"
```

---

### Task 3: 后端异常中间件与 ID 精度保护 (P1)

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: 统一异常捕获中的响应类**
修改 `backend/app/main.py` 的 `catch_exceptions_middleware`:
```python
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.error(traceback.format_exc())
        # Use SnowflakeJSONResponse for consistency and performance
        from app.main import SnowflakeJSONResponse
        return SnowflakeJSONResponse(
            status_code=500, content={"detail": "Internal Server Error"}
        )
```

- [ ] **Step 2: Commit**
```bash
git add backend/app/main.py
git commit -m "fix: use SnowflakeJSONResponse in exception middleware"
```

---

### Task 4: Dashboard 逻辑修复与递归统计 (P1)

**Files:**
- Modify: `backend/app/api/endpoints/dashboard.py`

- [ ] **Step 1: 修正 Dashboard 权限与统计逻辑**
重写 `get_dashboard_stats`：
1. 使用 `get_current_org_user` 获取 `org_user`。
2. 实现递归组织 ID 获取函数。
3. 修复对 `current_user.org_id` 的不当访问。

```python
async def get_org_tree_ids(db: AsyncSession, root_org_id: int) -> list[int]:
    query = text("""
        WITH RECURSIVE org_tree AS (
            SELECT id FROM organizations WHERE id = :root_id
            UNION ALL
            SELECT o.id FROM organizations o INNER JOIN org_tree ot ON o.parent_id = ot.id
        )
        SELECT id FROM org_tree
    """)
    result = await db.execute(query, {"root_id": root_org_id})
    return [row[0] for row in result.fetchall()]

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    org_user: OrganizationUser = Depends(get_current_org_user),
    db: AsyncSession = Depends(get_db),
    x_organization_id: int | None = Header(None)
):
    # 如果是 platform_admin 且没有传 Header，则查全量
    is_platform_admin = any(r.code == "platform_admin" for r in org_user.rbac_roles)
    
    target_org_ids = None
    if not (is_platform_admin and not x_organization_id):
        base_org_id = x_organization_id or org_user.org_id
        target_org_ids = await get_org_tree_ids(db, base_org_id)

    # ... 使用 target_org_ids 执行统计查询 (IN 语句)
```

- [ ] **Step 2: Commit**
```bash
git add backend/app/api/endpoints/dashboard.py
git commit -m "fix: refactor dashboard stats with recursive org support and proper RBAC"
```

---

### Task 5: 前端类型全面字符串化 (P2)

**Files:**
- Modify: `frontend/src/services/api/resources.ts`
- Modify: `frontend/src/services/api/auth.ts`
- Modify: 遍历 `frontend/src/pages/` 下涉及 ID 的组件。

- [ ] **Step 1: 修改 API 接口定义**
将 `resources.ts` 和 `auth.ts` 中的 `orgId: number` 等改为 `orgId: string`。

- [ ] **Step 2: 修改组件中的 ID 类型**
搜索项目中的 `number` 类型的 ID 声明，将其改为 `string`。

- [ ] **Step 3: 验证前端编译通过**
Run: `cd frontend && pnpm tsc`

- [ ] **Step 4: Commit**
```bash
git add frontend/
git commit -m "refactor: change all ID types from number to string in frontend"
```
