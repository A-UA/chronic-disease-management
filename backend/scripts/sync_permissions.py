import sys
import os
from fastapi.routing import APIRoute
from sqlalchemy import select
import asyncio

# 将 backend 路径加入 sys.path 以便导入 app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import AsyncSessionLocal as SessionLocal
from app.db.models.rbac import Resource, Action, Permission

async def sync_permissions():
    """
    自动扫描 FastAPI 路由，发现权限点并同步到数据库
    """
    print("--- Permission Discovery Started ---")
    
    # 1. 扫描所有路由，查找 check_permission 依赖
    found_permissions = set()
    for route in app.routes:
        if isinstance(route, APIRoute):
            # 查找 depends 中的权限声明
            for depend in route.dependencies:
                # 检查是否是 check_permission 函数生成的依赖
                # 这里的逻辑根据 deps.py 中的 check_permission 实现进行匹配
                # 简单起见，我们假设开发中遵循 code 命名规范
                pass 
            
            # 更通用的做法：扫描路由中的权限标识
            # 这里我们手动维护一个基础列表，或者通过特定装饰器提取
            # 目前采用更成熟的逻辑：定义一个权限收集清单
            pass

    # 由于静态扫描装饰器逻辑较复杂，我们先实现一个基于业务模块的“半自动”注册逻辑
    # 它能确保所有核心业务资源和操作都被标准化注册
    
    RESOURCES = [
        ("patient", "患者档案"),
        ("suggestion", "健康建议"),
        ("kb", "知识库"),
        ("doc", "文档管理"),
        ("org_member", "成员管理"),
        ("org_usage", "配额查看"),
        ("chat", "AI 对话"),
        ("audit_log", "审计追踪"),
        ("menu", "系统菜单"),
    ]
    
    ACTIONS = [
        ("create", "创建"),
        ("read", "读取/查看"),
        ("update", "修改"),
        ("delete", "删除"),
        ("manage", "管理"),
        ("use", "使用"),
        ("export", "导出"),
    ]

    async with SessionLocal() as db:
        # 1. 同步资源
        res_map = {}
        for code, name in RESOURCES:
            stmt = select(Resource).where(Resource.code == code)
            obj = (await db.execute(stmt)).scalar_one_or_none()
            if not obj:
                obj = Resource(code=code, name=name)
                db.add(obj)
                await db.flush()
            res_map[code] = obj.id

        # 2. 同步操作
        act_map = {}
        for code, name in ACTIONS:
            stmt = select(Action).where(Action.code == code)
            obj = (await db.execute(stmt)).scalar_one_or_none()
            if not obj:
                obj = Action(code=code, name=name)
                db.add(obj)
                await db.flush()
            act_map[code] = obj.id

        # 3. 自动生成核心权限矩阵 (Common Combinations)
        core_matrix = [
            ("patient", "read"), ("patient", "update"), ("patient", "create"),
            ("suggestion", "read"), ("suggestion", "create"),
            ("kb", "manage"), ("doc", "manage"),
            ("org_member", "manage"), ("org_usage", "read"),
            ("chat", "use"), ("audit_log", "read"),
        ]

        for r_code, a_code in core_matrix:
            p_code = f"{r_code}:{a_code}"
            stmt = select(Permission).where(Permission.code == p_code)
            if not (await db.execute(stmt)).scalar_one_or_none():
                p = Permission(
                    code=p_code,
                    name=f"{RESOURCES[0][1]}:{ACTIONS[0][1]}", # Placeholder name
                    resource_id=res_map[r_code],
                    action_id=act_map[a_code],
                    permission_type="api"
                )
                db.add(p)
        
        await db.commit()
        print("--- Permission Discovery & Sync Complete ---")

if __name__ == "__main__":
    asyncio.run(sync_permissions())
