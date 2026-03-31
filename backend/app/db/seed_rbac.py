import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import AsyncSessionLocal as SessionLocal
from app.db.models.rbac import Permission, Role, Resource, Action

# 1. Define Resources
RESOURCES = [
    {"name": "Patient Profile", "code": "patient", "description": "患者档案数据"},
    {"name": "Management Suggestion", "code": "suggestion", "description": "慢病管理建议"},
    {"name": "Knowledge Base", "code": "kb", "description": "RAG 知识库"},
    {"name": "Document", "code": "doc", "description": "知识库文档"},
    {"name": "Organization User", "code": "org_member", "description": "机构成员管理"},
    {"name": "Organization Usage", "code": "org_usage", "description": "机构配额与使用量"},
    {"name": "AI Chat", "code": "chat", "description": "AI 问答服务"},
    {"name": "Platform Settings", "code": "platform_settings", "description": "平台全局设置"},
    {"name": "Audit Log", "code": "audit_log", "description": "审计日志"},
    {"name": "Menu System", "code": "menu", "description": "UI 导航菜单"},
]

# 2. Define Actions
ACTIONS = [
    {"name": "Create", "code": "create"},
    {"name": "Read", "code": "read"},
    {"name": "Update", "code": "update"},
    {"name": "Delete", "code": "delete"},
    {"name": "Manage", "code": "manage"},
    {"name": "Use", "code": "use"},
    {"name": "View", "code": "view"},
    # Menu Actions
    {"name": "Dashboard", "code": "dashboard"},
    {"name": "Patients", "code": "patients"},
    {"name": "Knowledge", "code": "kb"},
    {"name": "Chat", "code": "chat"},
    {"name": "Settings", "code": "settings"},
]

# 3. Define Permissions (Resource + Action + UI)
# Format: (resource_code, action_code, permission_name, type, ui_metadata)
PERMISSION_MAP = [
    ("patient", "read", "查看患者", "api", None),
    ("patient", "update", "修改患者", "api", None),
    ("suggestion", "create", "创建建议", "api", None),
    ("suggestion", "read", "查看建议", "api", None),
    ("kb", "manage", "管理知识库", "api", None),
    ("doc", "manage", "管理文档", "api", None),
    ("org_member", "manage", "管理成员", "api", None),
    ("org_usage", "read", "查看使用量", "api", None),
    ("chat", "use", "使用 AI 对话", "api", None),
    ("platform_settings", "manage", "管理系统设置", "api", None),
    ("audit_log", "read", "查看审计日志", "api", None),
    
    # Menu Permissions
    ("menu", "dashboard", "控制台菜单", "menu", {"path": "/dashboard", "icon": "DashboardOutlined", "sort": 1}),
    ("menu", "patients", "患者管理菜单", "menu", {"path": "/patients", "icon": "TeamOutlined", "sort": 2}),
    ("menu", "kb", "知识库菜单", "menu", {"path": "/knowledge", "icon": "BookOutlined", "sort": 3}),
    ("menu", "chat", "AI 问答菜单", "menu", {"path": "/chat", "icon": "MessageOutlined", "sort": 4}),
    ("menu", "settings", "设置菜单", "menu", {"path": "/settings", "icon": "SettingOutlined", "sort": 10}),
]

# 4. Define Roles with Inheritance
ROLES = [
    ("staff", "基础成员", "机构基础职员", ["chat:use", "patient:read", "suggestion:read", "menu:dashboard", "menu:patients", "menu:chat"], None),
    ("manager", "管理人员", "健康管理师/主治医", ["suggestion:create", "patient:update"], "staff"),
    ("admin", "管理员", "机构系统管理员", ["kb:manage", "doc:manage", "org_member:manage", "org_usage:read", "menu:kb", "menu:settings"], "manager"),
    ("owner", "所有者", "机构主账户", [], "admin"),
    
    # Platform Roles (org_id is NULL)
    ("platform_viewer", "平台查看者", "平台级只读权限", ["audit_log:read"], None),
    ("platform_admin", "平台管理员", "平台最高管理员", ["platform_settings:manage"], "platform_viewer"),
]

async def seed_rbac():
    async with SessionLocal() as db:
        print("--- RBAC 3.0 Seeding (v2: Menus) Started ---")

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
        print("--- RBAC 3.0 Seeding (v2: Menus) Complete! ---")

if __name__ == "__main__":
    asyncio.run(seed_rbac())
