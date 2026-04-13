"""RBAC 业务服务（扩展版）

原有 RBACService 保留 SSD 约束校验，新增角色 CRUD 操作。
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.base.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models import (
    Action,
    OrganizationUserRole,
    Permission,
    Resource,
    Role,
)
from app.services.audit.service import audit_action


class RBACServiceExt:
    """扩展 RBAC 服务，提供角色 CRUD + 用户角色分配"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_resources(self) -> list[dict]:
        """系统资源字典"""
        result = await self.db.execute(select(Resource))
        return [{"id": r.id, "name": r.name, "code": r.code} for r in result.scalars().all()]

    async def list_actions(self) -> list[dict]:
        """系统操作字典"""
        result = await self.db.execute(select(Action))
        return [{"id": a.id, "name": a.name, "code": a.code} for a in result.scalars().all()]

    async def list_permissions(self) -> list[dict]:
        """系统权限列表"""
        result = await self.db.execute(select(Permission))
        return [{"id": p.id, "name": p.name, "code": p.code} for p in result.scalars().all()]

    async def list_roles(self, tenant_id: int, org_id: int) -> list[dict]:
        """获取组织可用角色列表（含用户计数）"""
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where((Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)))
        )
        result = await self.db.execute(stmt)
        roles = result.scalars().all()

        items = []
        for role in roles:
            count_stmt = select(func.count()).where(OrganizationUserRole.role_id == role.id)
            user_count = (await self.db.execute(count_stmt)).scalar() or 0
            items.append({
                "id": role.id,
                "name": role.name,
                "code": role.code,
                "description": role.description,
                "is_system": role.is_system,
                "parent_role_id": role.parent_role_id,
                "permissions": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "code": p.code,
                        "permission_type": p.permission_type,
                        "ui_metadata": p.ui_metadata,
                    }
                    for p in role.permissions
                ],
                "user_count": user_count,
            })
        return items

    async def create_role(
        self,
        *,
        tenant_id: int,
        org_id: int,
        admin_user_id: int,
        name: str,
        code: str,
        description: str | None,
        parent_role_id: int | None,
        permission_ids: list[int] | None,
    ) -> Role:
        """创建自定义角色"""
        stmt = select(Role).where(Role.tenant_id == tenant_id, Role.code == code)
        if (await self.db.execute(stmt)).scalar_one_or_none():
            raise ConflictError("Role code already exists in this organization")

        if parent_role_id:
            parent = await self.db.get(Role, parent_role_id)
            if not parent or (parent.tenant_id is not None and parent.tenant_id != tenant_id):
                raise NotFoundError("Parent role")

        role = Role(
            tenant_id=tenant_id,
            name=name,
            code=code,
            description=description,
            parent_role_id=parent_role_id,
            is_system=False,
        )

        if permission_ids:
            stmt_p = select(Permission).where(Permission.id.in_(permission_ids))
            perms = (await self.db.execute(stmt_p)).scalars().all()
            role.permissions = list(perms)

        self.db.add(role)
        await self.db.flush()

        await audit_action(
            self.db,
            user_id=admin_user_id,
            org_id=org_id,
            action="CREATE_ROLE",
            resource_type="role",
            resource_id=role.id,
            details=f"Created custom role: {role.code}",
        )

        await self.db.commit()
        await self.db.refresh(role, ["permissions"])
        return role

    async def assign_user_roles(
        self,
        *,
        tenant_id: int,
        org_id: int,
        admin_user_id: int,
        user_id: int,
        role_ids: list[int],
    ) -> dict:
        """为组织成员授权（含 SSD 约束校验）"""
        from app.services.system.rbac import RBACService

        # 验证角色可见性
        stmt_v = select(Role).where(
            Role.id.in_(role_ids),
            (Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)),
        )
        valid_roles = (await self.db.execute(stmt_v)).scalars().all()
        if len(valid_roles) != len(role_ids):
            raise NotFoundError("One or more roles are invalid")

        # SSD 约束校验
        conflict_msg = await RBACService.check_ssd_violation(self.db, tenant_id, role_ids)
        if conflict_msg:
            raise ForbiddenError(conflict_msg)

        # 先删旧的
        old_stmt = select(OrganizationUserRole).where(
            OrganizationUserRole.org_id == org_id, OrganizationUserRole.user_id == user_id
        )
        old_links = (await self.db.execute(old_stmt)).scalars().all()
        for link in old_links:
            await self.db.delete(link)

        # 添新的
        for rid in role_ids:
            self.db.add(
                OrganizationUserRole(
                    tenant_id=tenant_id, org_id=org_id, user_id=user_id, role_id=rid
                )
            )

        await audit_action(
            self.db,
            user_id=admin_user_id,
            org_id=org_id,
            action="ASSIGN_ROLES",
            resource_type="user",
            resource_id=user_id,
            details=f"Assigned roles {role_ids} to user {user_id}",
        )

        await self.db.commit()
        return {"status": "ok", "assigned_roles": [r.code for r in valid_roles]}

    async def update_role(
        self, role_id: int, tenant_id: int, data: dict
    ) -> dict:
        """更新自定义角色"""
        role = await self.db.get(Role, role_id)
        if not role or role.tenant_id != tenant_id:
            raise NotFoundError("Role", role_id)
        if role.is_system:
            raise ForbiddenError("Cannot modify system roles")

        if "name" in data and data["name"] is not None:
            role.name = data["name"]
        if "description" in data and data["description"] is not None:
            role.description = data["description"]
        if "permission_ids" in data and data["permission_ids"] is not None:
            stmt = select(Permission).where(Permission.id.in_(data["permission_ids"]))
            perms = (await self.db.execute(stmt)).scalars().all()
            role.permissions = list(perms)

        await self.db.commit()
        await self.db.refresh(role, ["permissions"])
        return {
            "id": role.id,
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_system": role.is_system,
        }

    async def delete_role(self, role_id: int, tenant_id: int) -> None:
        """删除自定义角色"""
        role = await self.db.get(Role, role_id)
        if not role or role.tenant_id != tenant_id:
            raise NotFoundError("Role", role_id)
        if role.is_system:
            raise ForbiddenError("Cannot delete system roles")

        bound_stmt = select(OrganizationUserRole).where(OrganizationUserRole.role_id == role_id)
        bound = (await self.db.execute(bound_stmt)).scalars().first()
        if bound:
            raise ConflictError("Role is still assigned to users. Unassign first.")

        await self.db.delete(role)
        await self.db.commit()
