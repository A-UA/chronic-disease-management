"""API 测试公用 fixture 与辅助工具

统一定义 mock 数据和依赖覆盖，确保与新的多租户认证体系一致。
依赖链：
  inject_rls_context → 返回 tenant_id（同时注入 RLS 上下文）
  get_current_tenant_id → 返回 tenant_id
  get_current_org_id → 返回 org_id
  get_effective_org_id → admin 返回 None，staff 返回 org_id
  get_current_user → 返回 User mock
  get_current_org_user → 返回 OrganizationUser mock
  get_current_roles → 返回角色列表
  check_permission → 通过 mock RBACService 放行
  check_org_admin → 通过 mock RBACService 放行
  get_db → 返回 AsyncMock() session
"""
from unittest.mock import MagicMock, AsyncMock, patch

from app.api.deps import (
    get_current_user, get_current_tenant_id, get_current_org_id,
    get_effective_org_id, get_current_roles, inject_rls_context,
    get_current_org_user, get_current_org, get_db,
)

# ── 常量 ──
TENANT_ID = 3001
ORG_ID = 2001
USER_ID = 1001

# ── 权限 mock 列表（覆盖所有已知权限） ──
ALL_PERMISSIONS = {
    "patient:read", "patient:create", "patient:update", "patient:delete",
    "suggestion:read", "suggestion:create",
    "chat:use", "kb:manage", "doc:manage",
    "org_member:manage", "org_usage:read", "audit_log:read",
    "org:manage", "platform:manage",
}


# ── Mock 工厂 ──

def make_user(uid=USER_ID, email="test@example.com", name="测试用户"):
    u = MagicMock()
    u.id = uid
    u.email = email
    u.name = name
    u.password_hash = "$argon2id$fake"
    return u


def make_org_user(user_id=USER_ID, org_id=ORG_ID, tenant_id=TENANT_ID,
                  user_type="staff"):
    ou = MagicMock()
    ou.user_id = user_id
    ou.org_id = org_id
    ou.tenant_id = tenant_id
    ou.user_type = user_type
    role = MagicMock()
    role.id = 1
    role.code = "admin"
    ou.rbac_roles = [role]
    return ou


# ── 统一依赖覆盖 ──

def override_deps(app, db=None, user=None, uid=USER_ID, org_id=ORG_ID,
                  tenant_id=TENANT_ID, effective_org_id=ORG_ID,
                  roles=None, permissions=None):
    """一键覆盖所有认证和上下文依赖 + mock RBACService。

    参数：
        effective_org_id: 传 None 模拟 admin 跨部门访问，传 int 模拟 staff 限定部门
        roles: 角色列表，默认 ["admin"]
        permissions: 权限集合，默认 ALL_PERMISSIONS（全放行）
    """
    _user = user or make_user(uid)
    _db = db or AsyncMock()
    _roles = roles or ["admin"]
    _org_user = make_org_user(user_id=uid, org_id=org_id, tenant_id=tenant_id)
    _perms = permissions or ALL_PERMISSIONS

    # 核心认证
    app.dependency_overrides[get_current_user] = lambda: _user
    app.dependency_overrides[get_current_tenant_id] = lambda: tenant_id
    app.dependency_overrides[get_current_org_id] = lambda: org_id
    app.dependency_overrides[get_current_roles] = lambda: _roles
    app.dependency_overrides[get_effective_org_id] = lambda: effective_org_id
    app.dependency_overrides[inject_rls_context] = lambda: tenant_id
    app.dependency_overrides[get_current_org] = lambda: org_id
    app.dependency_overrides[get_current_org_user] = lambda: _org_user
    app.dependency_overrides[get_db] = lambda: _db

    # 不再通过覆盖工厂函数放行权限，而是 mock RBACService
    # check_permission/check_org_admin 的内部子依赖 (get_current_org_user, get_db)
    # 已覆盖，但 RBACService 的静态方法需要正确处理 AsyncMock db

    return _db, _user


# ── RBACService patch 辅助 ──

def patch_rbac(permissions=None):
    """返回可用于 @patch 的上下文管理器或 decorator。

    用法：
        with patch_rbac_all():
            ...
    """
    _perms = permissions or ALL_PERMISSIONS

    patcher_perms = patch(
        "app.services.rbac.RBACService.get_effective_permissions",
        new_callable=AsyncMock, return_value=_perms,
    )
    patcher_roles = patch(
        "app.services.rbac.RBACService.get_all_role_ids",
        new_callable=AsyncMock, return_value={1},
    )
    return patcher_perms, patcher_roles


class PatchRBAC:
    """上下文管理器，同时激活 RBACService 的两个 mock"""

    def __init__(self, permissions=None):
        self._perms = permissions or ALL_PERMISSIONS

    def __enter__(self):
        self._p1 = patch(
            "app.services.rbac.RBACService.get_effective_permissions",
            new_callable=AsyncMock, return_value=self._perms,
        )
        self._p2 = patch(
            "app.services.rbac.RBACService.get_all_role_ids",
            new_callable=AsyncMock, return_value={1},
        )
        self._p1.start()
        self._p2.start()
        return self

    def __exit__(self, *args):
        self._p1.stop()
        self._p2.stop()


class MockScalarResult:
    """模拟 db.execute() 返回的结果对象"""
    def __init__(self, items=None, scalar_value=None):
        self._items = items or []
        self._scalar_value = scalar_value

    def scalars(self):
        mock = MagicMock()
        mock.all.return_value = self._items
        mock.first.return_value = self._items[0] if self._items else None
        return mock

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

    def scalar(self):
        return self._scalar_value

    def fetchall(self):
        return self._items
