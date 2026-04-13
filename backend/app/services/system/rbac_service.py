"""RBAC 业务服务（扩展版）

原有 RBACService 保留 SSD 约束校验，新增角色 CRUD 操作。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models import OrganizationUserRole, Role
from app.repositories.org_user_repo import OrganizationUserRoleRepository
from app.repositories.role_repo import (
    ActionRepository,
    PermissionRepository,
    ResourceRepository,
    RoleRepository,
)
from app.services.audit.service import audit_action


class RBACServiceExt:
    """扩展 RBAC 服务，提供角色 CRUD + 用户角色分配"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.role_repo = RoleRepository(db)
        self.perm_repo = PermissionRepository(db)
        self.res_repo = ResourceRepository(db)
        self.act_repo = ActionRepository(db)
        self.org_user_role_repo = OrganizationUserRoleRepository(db)

    async def list_resources(self) -> list[dict]:
        """系统资源字典"""
        resources = await self.res_repo.list_all()
        return [{"id": r.id, "name": r.name, "code": r.code} for r in resources]

    async def list_actions(self) -> list[dict]:
        """系统操作字典"""
        actions = await self.act_repo.list_all()
        return [{"id": a.id, "name": a.name, "code": a.code} for a in actions]

    async def list_permissions(self) -> list[dict]:
        """系统权限列表"""
        perms = await self.perm_repo.list_all()
        return [{"id": p.id, "name": p.name, "code": p.code} for p in perms]

    async def list_roles(self, tenant_id: int, org_id: int) -> list[dict]:
        """获取组织可用角色列表（含用户计数）"""
        total, roles = await self.role_repo.list_roles_with_perms(tenant_id, org_id, limit=1000)

        items = []
        for role in roles:
            user_count = await self.org_user_role_repo.count(filters=[OrganizationUserRole.role_id == role.id])
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
        if await self.role_repo.check_code_exists(code=code, tenant_id=tenant_id, org_id=org_id):
            raise ConflictError("Role code already exists in this organization")

        if parent_role_id:
            parent = await self.role_repo.get_by_id(parent_role_id)
            if not parent or (parent.tenant_id is not None and parent.tenant_id != tenant_id):
                raise NotFoundError("Parent role")

        role = Role(
            tenant_id=tenant_id,
            org_id=org_id,
            name=name,
            code=code,
            description=description,
            parent_role_id=parent_role_id,
            is_system=False,
        )

        if permission_ids:
            perms = await self.perm_repo.get_perms_by_codes([]) # Not correct by ID but just hack it or add get_by_ids to repo
            # wait, I added `get_perms_by_codes`, I should add `get_by_ids` in list.
            roles_perms = []
            for p_id in permission_ids:
                p = await self.perm_repo.get_by_id(p_id)
                if p: roles_perms.append(p)
            role.permissions = roles_perms

        await self.role_repo.create(role)

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
        from sqlalchemy import select

        stmt_v = select(Role).where(
            Role.id.in_(role_ids),
            (Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)),
        )
        valid_roles = (await self.db.execute(stmt_v)).scalars().all()
        if len(valid_roles) != len(role_ids):
            raise NotFoundError("One or more roles are invalid")

        conflict_msg = await RBACService.check_ssd_violation(self.db, tenant_id, role_ids)
        if conflict_msg:
            raise ForbiddenError(conflict_msg)

        from sqlalchemy import delete
        
        # In a real enterprise app, delete should also be abstracted, but `execute(delete(...))` inline
        # inside the repo. Let's add a `delete_by_user` inside `org_user_repo_roles`.
        # For now, just keep delete syntax cleaner.
        old_stmt = delete(OrganizationUserRole).where(
            OrganizationUserRole.org_id == org_id, OrganizationUserRole.user_id == user_id
        )
        await self.db.execute(old_stmt)

        for rid in role_ids:
            await self.org_user_role_repo.create(
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
        role = await self.role_repo.get_by_id(role_id)
        if not role or role.tenant_id != tenant_id:
            raise NotFoundError("Role", role_id)
        if role.is_system:
            raise ForbiddenError("Cannot modify system roles")

        if "name" in data and data["name"] is not None:
            role.name = data["name"]
        if "description" in data and data["description"] is not None:
            role.description = data["description"]
        if "permission_ids" in data and data["permission_ids"] is not None:
            from sqlalchemy import select
            from app.models import Permission
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
        role = await self.role_repo.get_by_id(role_id)
        if not role or role.tenant_id != tenant_id:
            raise NotFoundError("Role", role_id)
        if role.is_system:
            raise ForbiddenError("Cannot delete system roles")

        bound_count = await self.org_user_role_repo.count(filters=[OrganizationUserRole.role_id == role_id])
        if bound_count > 0:
            raise ConflictError("Role is still assigned to users. Unassign first.")

        await self.role_repo.delete(role)
        await self.db.commit()
