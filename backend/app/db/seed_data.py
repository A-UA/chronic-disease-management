"""统一种子数据初始化脚本

包含：RBAC（资源/操作/权限/角色）、菜单、超管账号

用法：
    cd backend
    uv run python -m app.db.seed_data
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal as SessionLocal
from app.db.models.rbac import Permission, Role, Resource, Action
from app.db.models.menu import Menu


# ═══════════════════════════════════════════════════════════
#  1. RBAC 数据定义
# ═══════════════════════════════════════════════════════════

RESOURCES = [
    {"name": "Patient Profile", "code": "patient", "description": "患者档案数据"},
    {"name": "Management Suggestion", "code": "suggestion", "description": "慢病管理建议"},
    {"name": "Knowledge Base", "code": "kb", "description": "RAG 知识库"},
    {"name": "Document", "code": "doc", "description": "知识库文档"},
    {"name": "Organization User", "code": "org_member", "description": "机构成员管理"},
    {"name": "Organization Usage", "code": "org_usage", "description": "机构配额与使用量"},
    {"name": "AI Chat", "code": "chat", "description": "AI 问答服务"},
    {"name": "Audit Log", "code": "audit_log", "description": "审计日志"},
]

ACTIONS = [
    {"name": "Manage", "code": "manage"},
    {"name": "Create", "code": "create"},
    {"name": "Read", "code": "read"},
    {"name": "Update", "code": "update"},
    {"name": "Delete", "code": "delete"},
    {"name": "Use", "code": "use"},
]

# 纯 API 权限，菜单可见性由 menus 表的 permission_code 字段控制
PERMISSION_MAP = [
    # (resource_code, action_code, display_name, permission_type, ui_metadata)
    ("patient", "read", "查看患者", "api", None),
    ("patient", "create", "创建患者", "api", None),
    ("patient", "update", "修改患者", "api", None),
    ("patient", "delete", "删除患者", "api", None),
    ("suggestion", "create", "创建建议", "api", None),
    ("suggestion", "read", "查看建议", "api", None),
    ("kb", "manage", "管理知识库", "api", None),
    ("doc", "manage", "管理文档", "api", None),
    ("org_member", "manage", "管理成员", "api", None),
    ("org_usage", "read", "查看使用量", "api", None),
    ("chat", "use", "使用 AI 对话", "api", None),
    ("audit_log", "read", "查看审计日志", "api", None),
]

# 角色只分配 API 权限；菜单可见性通过 menus.permission_code 自动关联
ROLES = [
    # (code, name, description, [直接权限], parent_code)
    ("staff", "基础成员", "机构基础职员",
     ["chat:use", "patient:read", "suggestion:read"],
     None),
    ("manager", "管理人员", "健康管理师/主治医",
     ["patient:create", "patient:update", "suggestion:create"],
     "staff"),
    ("admin", "管理员", "机构系统管理员",
     ["patient:delete", "kb:manage", "doc:manage", "org_member:manage", "org_usage:read", "audit_log:read"],
     "manager"),
    ("owner", "所有者", "机构主账户",
     [],
     "admin"),
]


# ═══════════════════════════════════════════════════════════
#  2. 菜单数据定义（与 RBAC permission_code 对齐）
# ═══════════════════════════════════════════════════════════

SYSTEM_MENUS = [
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


# ═══════════════════════════════════════════════════════════
#  3. 超管账号
# ═══════════════════════════════════════════════════════════

SUPER_ADMIN = {
    "email": "admin@cdm.local",
    "password": "Admin@2026",
    "name": "系统超管",
}

DEFAULT_ORG = {
    "name": "默认组织",
    "plan_type": "enterprise",
}


# ═══════════════════════════════════════════════════════════
#  执行函数
# ═══════════════════════════════════════════════════════════

async def seed_rbac(db):
    """初始化 RBAC：资源 → 操作 → 权限 → 角色"""
    print("=== [1/3] RBAC 种子数据 ===")

    # Resources
    resource_objs = {}
    for r_data in RESOURCES:
        stmt = select(Resource).where(Resource.code == r_data["code"])
        obj = (await db.execute(stmt)).scalar_one_or_none()
        if not obj:
            obj = Resource(**r_data)
            db.add(obj)
            await db.flush()
            print(f"  + Resource: {r_data['code']}")
        resource_objs[r_data["code"]] = obj

    # Actions
    action_objs = {}
    for a_data in ACTIONS:
        stmt = select(Action).where(Action.code == a_data["code"])
        obj = (await db.execute(stmt)).scalar_one_or_none()
        if not obj:
            obj = Action(**a_data)
            db.add(obj)
            await db.flush()
            print(f"  + Action: {a_data['code']}")
        action_objs[a_data["code"]] = obj

    # Permissions
    permission_objs = {}
    for r_code, a_code, p_name, p_type, ui_meta in PERMISSION_MAP:
        p_code = f"{r_code}:{a_code}"
        stmt = select(Permission).where(Permission.code == p_code)
        obj = (await db.execute(stmt)).scalar_one_or_none()
        if not obj:
            obj = Permission(
                name=p_name, code=p_code,
                resource_id=resource_objs[r_code].id,
                action_id=action_objs[a_code].id,
                permission_type=p_type, ui_metadata=ui_meta,
            )
            db.add(obj)
            await db.flush()
            print(f"  + Permission: {p_code}")
        else:
            obj.permission_type = p_type
            obj.ui_metadata = ui_meta
            obj.name = p_name
        permission_objs[p_code] = obj

    # Roles (pass 1: create)
    role_objs = {}
    for r_code, r_name, r_desc, p_codes, _ in ROLES:
        stmt = (select(Role)
                .where(Role.code == r_code, Role.org_id == None)
                .options(selectinload(Role.permissions)))
        role = (await db.execute(stmt)).scalar_one_or_none()
        perms = [permission_objs[c] for c in p_codes]
        if not role:
            role = Role(name=r_name, code=r_code, description=r_desc, is_system=True)
            role.permissions = perms
            db.add(role)
            await db.flush()
            print(f"  + Role: {r_code}")
        else:
            role.permissions = perms
        role_objs[r_code] = role

    # Roles (pass 2: inheritance)
    for r_code, _, _, _, parent_code in ROLES:
        if parent_code:
            role_objs[r_code].parent_role_id = role_objs[parent_code].id

    print("  [OK] RBAC done")
    return role_objs


async def seed_menus(db):
    """初始化菜单树"""
    print("=== [2/3] 菜单种子数据 ===")

    parent_map = {}
    for menu_data in SYSTEM_MENUS:
        stmt = select(Menu).where(Menu.code == menu_data["code"])
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if not existing:
            menu = Menu(**menu_data)
            db.add(menu)
            await db.flush()
            parent_map[menu.code] = menu.id
            print(f"  + Menu: {menu.name} ({menu.code})")
        else:
            parent_map[existing.code] = existing.id

    for parent_code, children in CHILD_MENUS.items():
        parent_id = parent_map.get(parent_code)
        if not parent_id:
            print(f"  [WARN] Parent {parent_code} not found, skipping")
            continue
        for child_data in children:
            stmt = select(Menu).where(Menu.code == child_data["code"])
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if not existing:
                child = Menu(parent_id=parent_id, **child_data)
                db.add(child)
                print(f"    + Child: {child.name} ({child.code})")

    print("  [OK] Menus done")


async def seed_super_admin(db, role_objs: dict):
    """预制超管账号：默认组织 + 超管用户 + owner 角色"""
    from app.core.security import get_password_hash
    from app.db.models.user import User
    from app.db.models.organization import (
        Organization, OrganizationUser, OrganizationUserRole,
    )

    print("=== [3/3] 超管账号 ===")

    # 幂等检查
    stmt = select(User).where(User.email == SUPER_ADMIN["email"])
    if (await db.execute(stmt)).scalar_one_or_none():
        print(f"  [SKIP] {SUPER_ADMIN['email']} already exists")
        return

    # 创建默认组织
    org = Organization(**DEFAULT_ORG)
    db.add(org)
    await db.flush()
    print(f"  + Org: {org.name} (id={org.id})")

    # 创建超管用户
    user = User(
        email=SUPER_ADMIN["email"],
        password_hash=get_password_hash(SUPER_ADMIN["password"]),
        name=SUPER_ADMIN["name"],
    )
    db.add(user)
    await db.flush()
    print(f"  + User: {user.email} (id={user.id})")

    # 关联到组织
    org_user = OrganizationUser(org_id=org.id, user_id=user.id, user_type="staff")
    db.add(org_user)
    await db.flush()

    # 分配 owner 角色
    owner_role = role_objs.get("owner")
    if owner_role:
        db.add(OrganizationUserRole(org_id=org.id, user_id=user.id, role_id=owner_role.id))
        print(f"  + Role: owner → {user.email}")
    else:
        print("  [WARN] owner role not found")

    print(f"  [OK] SuperAdmin ready: {SUPER_ADMIN['email']} / {SUPER_ADMIN['password']}")


async def main():
    """统一入口：在同一个事务中完成所有种子数据"""
    async with SessionLocal() as db:
        print("=========================================")
        print("  Chronic Disease Management")
        print("  Seed Data Initialization")
        print("=========================================")

        role_objs = await seed_rbac(db)
        await seed_menus(db)
        await seed_super_admin(db, role_objs)

        await db.commit()
        print("\n[DONE] All seed data initialized!")


if __name__ == "__main__":
    asyncio.run(main())
