"""菜单种子数据初始化脚本

用法：
    cd backend
    uv run python -m app.db.seed_menus
"""
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
                else:
                    print(f"    Exists: {existing.name} ({existing.code})")

        await db.commit()
        print("--- Menu Seeding Done ---")


if __name__ == "__main__":
    asyncio.run(seed_menus())
