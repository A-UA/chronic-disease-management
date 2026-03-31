import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import AsyncSessionLocal as SessionLocal
from app.db.models.rbac import Permission, Role, Resource, Action

# 1. Define Resources (Tenant-only focus)
RESOURCES = [
    {"name": "Patient Profile", "code": "patient", "description": "患者档案数据"},
    {"name": "Management Suggestion", "code": "suggestion", "description": "慢病管理建议"},
    {"name": "Knowledge Base", "code": "kb", "description": "RAG 知识库"},
    {"name": "Document", "code": "doc", "description": "知识库文档"},
    {"name": "Organization User", "code": "org_member", "description": "机构成员管理"},
    {"name": "Organization Usage", "code": "org_usage", "description": "机构配额与使用量"},
    {"name": "AI Chat", "code": "chat", "description": "AI 问答服务"},
    {"name": "Audit Log", "code": "audit_log", "description": "审计日志"},
    {"name": "Tenant Menu", "code": "menu", "description": "B端机构菜单"},
]

# 2. Define Actions
ACTIONS = [
    {"name": "Manage", "code": "manage"},
    {"name": "Use", "code": "use"},
    {"name": "Read", "code": "read"},
    {"name": "Update", "code": "update"},
    {"name": "Dashboard", "code": "dashboard"},
    {"name": "Patients", "code": "patients"},
    {"name": "Knowledge", "code": "kb"},
    {"name": "Chat", "code": "chat"},
    {"name": "Members", "code": "members"},
    {"name": "Roles", "code": "roles"},
    {"name": "Settings", "code": "settings"},
]

# 3. Define Permissions (Flat, Logical Paths)
PERMISSION_MAP = [
    # --- API Permissions ---
    ("patient", "read", "查看患者", "api", None),
    ("patient", "update", "修改患者", "api", None),
    ("suggestion", "create", "创建建议", "api", None),
    ("suggestion", "read", "查看建议", "api", None),
    ("kb", "manage", "管理知识库", "api", None),
    ("doc", "manage", "管理文档", "api", None),
    ("org_member", "manage", "管理成员", "api", None),
    ("org_usage", "read", "查看使用量", "api", None),
    ("chat", "use", "使用 AI 对话", "api", None),
    ("audit_log", "read", "查看审计日志", "api", None),
    
    # --- Unified B-Side Tenant Menus ---
    ("menu", "dashboard", "控制台", "menu", {"path": "/dashboard", "icon": "DashboardOutlined", "sort": 1}),
    ("menu", "patients", "患者管理", "menu", {"path": "/patients", "icon": "TeamOutlined", "sort": 2}),
    ("menu", "kb", "知识库管理", "menu", {"path": "/knowledge", "icon": "BookOutlined", "sort": 3}),
    ("menu", "chat", "AI 问答", "menu", {"path": "/chat", "icon": "MessageOutlined", "sort": 4}),
    ("menu", "members", "成员管理", "menu", {"path": "/members", "icon": "UserOutlined", "sort": 5}),
    ("menu", "roles", "角色权限", "menu", {"path": "/roles", "icon": "LockOutlined", "sort": 6}),
    ("menu", "settings", "操作审计", "menu", {"path": "/audit-logs", "icon": "SettingOutlined", "sort": 10}),
]

# 4. Define Roles with Inheritance (Pure Tenant Architecture)
ROLES = [
    ("staff", "基础成员", "机构基础职员", ["chat:use", "patient:read", "suggestion:read", "menu:dashboard", "menu:patients", "menu:chat"], None),
    ("manager", "管理人员", "健康管理师/主治医", ["suggestion:create", "patient:update"], "staff"),
    ("admin", "管理员", "机构系统管理员", ["kb:manage", "doc:manage", "org_member:manage", "org_usage:read", "menu:kb", "menu:members", "menu:roles", "menu:settings"], "manager"),
    ("owner", "所有者", "机构主账户", [], "admin"),
]

async def seed_rbac():
    async with SessionLocal() as db:
        print("--- RBAC 3.0 Seeding (v6: Tenant Equality) Started ---")

        # 1. Seed Resources
        resource_objs = {}
        for r_data in RESOURCES:
            stmt = select(Resource).where(Resource.code == r_data["code"])
            res = await db.execute(stmt)
            obj = res.scalar_one_or_none()
            if not obj:
                obj = Resource(**r_data)
                db.add(obj)
                await db.flush()
            resource_objs[r_data["code"]] = obj

        # 2. Seed Actions
        action_objs = {}
        for a_data in ACTIONS:
            stmt = select(Action).where(Action.code == a_data["code"])
            res = await db.execute(stmt)
            obj = res.scalar_one_or_none()
            if not obj:
                obj = Action(**a_data)
                db.add(obj)
                await db.flush()
            action_objs[a_data["code"]] = obj

        # 3. Seed Permissions
        permission_objs = {}
        for p_info in PERMISSION_MAP:
            r_code, a_code, p_name, p_type, ui_meta = p_info
            p_code = f"{r_code}:{a_code}"
            stmt = select(Permission).where(Permission.code == p_code)
            res = await db.execute(stmt)
            obj = res.scalar_one_or_none()
            if not obj:
                obj = Permission(
                    name=p_name,
                    code=p_code,
                    resource_id=resource_objs[r_code].id,
                    action_id=action_objs[a_code].id,
                    permission_type=p_type,
                    ui_metadata=ui_meta
                )
                db.add(obj)
                await db.flush()
            else:
                obj.permission_type = p_type
                obj.ui_metadata = ui_meta
                obj.name = p_name
            permission_objs[p_code] = obj

        # 4. Seed Roles
        role_objs = {}
        for r_code, r_name, r_desc, p_codes, parent_code in ROLES:
            stmt = select(Role).where(Role.code == r_code, Role.org_id == None).options(selectinload(Role.permissions))
            res = await db.execute(stmt)
            role = res.scalar_one_or_none()
            
            target_permissions = [permission_objs[code] for code in p_codes]

            if not role:
                role = Role(name=r_name, code=r_code, description=r_desc, is_system=True)
                role.permissions = target_permissions
                db.add(role)
                await db.flush()
            else:
                role.permissions = target_permissions
            
            role_objs[r_code] = role

        # 5. Seed Roles (Pass 2: Set inheritance)
        for r_code, _, _, _, parent_code in ROLES:
            if parent_code:
                role_objs[r_code].parent_role_id = role_objs[parent_code].id

        await db.commit()
        print("--- RBAC 3.0 Seeding (v6: Tenant Equality) Complete! ---")

if __name__ == "__main__":
    asyncio.run(seed_rbac())
