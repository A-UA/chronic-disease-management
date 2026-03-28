import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import AsyncSessionLocal as SessionLocal
from app.db.models.rbac import Permission, Role

PERMISSIONS = [
    {
        "name": "View Patients",
        "code": "patient:view",
        "description": "Can view patient profiles",
    },
    {
        "name": "Edit Patients",
        "code": "patient:edit",
        "description": "Can edit patient profiles",
    },
    {
        "name": "Create Suggestions",
        "code": "suggestion:create",
        "description": "Can write management suggestions",
    },
    {
        "name": "View Suggestions",
        "code": "suggestion:view",
        "description": "Can view management suggestions",
    },
    {
        "name": "Manage Knowledge Base",
        "code": "kb:manage",
        "description": "Can create/edit knowledge bases",
    },
    {
        "name": "Manage Documents",
        "code": "doc:manage",
        "description": "Can upload/delete documents",
    },
    {
        "name": "Manage Org Members",
        "code": "org:manage_members",
        "description": "Can invite/remove members",
    },
    {
        "name": "View Usage",
        "code": "org:view_usage",
        "description": "Can see token usage",
    },
    {"name": "Use AI Chat", "code": "chat:use", "description": "Can interact with AI"},
    # Platform-level permissions
    {
        "name": "Platform Manage Orgs",
        "code": "platform:manage_orgs",
        "description": "Can manage all organizations",
    },
    {
        "name": "Platform Manage Users",
        "code": "platform:manage_users",
        "description": "Can manage all users",
    },
    {
        "name": "Platform View Usage",
        "code": "platform:view_usage",
        "description": "Can view global usage",
    },
    {
        "name": "Platform Manage Settings",
        "code": "platform:manage_settings",
        "description": "Can manage system settings",
    },
    {
        "name": "Platform View Audit",
        "code": "platform:view_audit",
        "description": "Can view global audit logs",
    },
]

ROLES = [
    {
        "name": "Organization Owner",
        "code": "owner",
        "description": "Full access to the organization",
        "permissions": [
            "patient:view",
            "patient:edit",
            "suggestion:create",
            "suggestion:view",
            "kb:manage",
            "doc:manage",
            "org:manage_members",
            "org:view_usage",
            "chat:use",
        ],
    },
    {
        "name": "Admin",
        "code": "admin",
        "description": "Administrative access",
        "permissions": [
            "patient:view",
            "patient:edit",
            "suggestion:create",
            "suggestion:view",
            "kb:manage",
            "doc:manage",
            "org:manage_members",
            "org:view_usage",
            "chat:use",
        ],
    },
    {
        "name": "Manager",
        "code": "manager",
        "description": "Healthcare manager/professional",
        "permissions": [
            "patient:view",
            "patient:edit",
            "suggestion:create",
            "suggestion:view",
            "kb:manage",
            "doc:manage",
            "chat:use",
        ],
    },
    {
        "name": "Patient",
        "code": "patient",
        "description": "Default patient role",
        "permissions": ["patient:view", "chat:use"],
    },
    # Platform-level roles (org_id is NULL)
    {
        "name": "Platform Admin",
        "code": "platform_admin",
        "description": "Platform super administrator",
        "permissions": [
            "platform:manage_orgs",
            "platform:manage_users",
            "platform:view_usage",
            "platform:manage_settings",
            "platform:view_audit",
        ],
    },
    {
        "name": "Platform Viewer",
        "code": "platform_viewer",
        "description": "Platform read-only viewer",
        "permissions": ["platform:view_usage", "platform:view_audit"],
    },
]


async def seed_rbac():
    async with SessionLocal() as db:
        # 1. Seed Permissions
        print("Seeding Permissions...")
        permission_map = {}
        for p_data in PERMISSIONS:
            stmt = select(Permission).where(Permission.code == p_data["code"])
            res = await db.execute(stmt)
            permission = res.scalar_one_or_none()
            if not permission:
                permission = Permission(**p_data)
                db.add(permission)
                await db.flush()
            permission_map[p_data["code"]] = permission

        # 2. Seed Roles
        print("Seeding System Roles...")
        for r_data in ROLES:
            p_codes = r_data.pop("permissions")
            stmt = select(Role).where(Role.code == r_data["code"], Role.org_id == None)
            res = await db.execute(stmt)
            role = res.scalar_one_or_none()

            target_permissions = [permission_map[code] for code in p_codes]

            if not role:
                role = Role(**r_data, is_system=True)
                role.permissions = target_permissions
                db.add(role)
            else:
                # For existing roles, we need to refresh to avoid IO errors
                await db.refresh(role, ["permissions"])
                role.permissions = target_permissions

        await db.commit()
        print("RBAC Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_rbac())
