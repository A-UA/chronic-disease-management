from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.role_repo import RoleRepository, PermissionRepository, RoleConstraintRepository


class RBACService:
    @staticmethod
    async def get_all_role_ids(
        db: AsyncSession, direct_role_ids: list[int]
    ) -> set[int]:
        """
        使用递归 CTE 获取所有角色 ID (包括继承的父角色)
        """
        if not direct_role_ids:
            return set()
        repo = RoleRepository(db)
        return await repo.get_all_role_ids(direct_role_ids)

    @staticmethod
    async def get_effective_permissions(
        db: AsyncSession, role_ids: list[int]
    ) -> set[str]:
        """
        获取角色集合的最终有效权限代码集 (包含继承)
        """
        all_role_ids = await RBACService.get_all_role_ids(db, role_ids)
        if not all_role_ids:
            return set()

        repo = PermissionRepository(db)
        return await repo.get_codes_by_role_ids(list(all_role_ids))

    @staticmethod
    async def check_ssd_violation(
        db: AsyncSession, tenant_id: int | None, role_ids: list[int]
    ) -> str | None:
        """
        检查静态责任分离 (SSD) 冲突
        如果存在冲突，返回冲突描述字符串，否则返回 None
        """
        repo = RoleConstraintRepository(db)
        constraints = await repo.get_ssd_constraints(tenant_id)

        role_set = set(role_ids)
        for c in constraints:
            if c.role_id_1 in role_set and c.role_id_2 in role_set:
                return f"Conflict detected: Role {c.role_id_1} and Role {c.role_id_2} cannot be assigned together (SSD: {c.name})"

        return None
