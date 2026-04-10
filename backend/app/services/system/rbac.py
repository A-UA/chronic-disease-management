from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permission, Role, RoleConstraint


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

        # 定义递归 CTE 查询所有父角色
        query = text("""
            WITH RECURSIVE role_hierarchy AS (
                -- 初始：直接关联的角色
                SELECT id, parent_role_id
                FROM roles
                WHERE id = ANY(:role_ids)

                UNION

                -- 递归：查找父角色
                SELECT r.id, r.parent_role_id
                FROM roles r
                INNER JOIN role_hierarchy rh ON rh.parent_role_id = r.id
            )
            SELECT id FROM role_hierarchy;
        """)

        result = await db.execute(query, {"role_ids": direct_role_ids})
        return {row[0] for row in result.fetchall()}

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

        # 聚合所有角色的权限
        query = (
            select(Permission.code)
            .join(Permission.roles)
            .where(Role.id.in_(list(all_role_ids)))
        )

        result = await db.execute(query)
        return {row[0] for row in result.fetchall()}

    @staticmethod
    async def check_ssd_violation(
        db: AsyncSession, tenant_id: int | None, role_ids: list[int]
    ) -> str | None:
        """
        检查静态责任分离 (SSD) 冲突
        如果存在冲突，返回冲突描述字符串，否则返回 None
        """
        stmt = select(RoleConstraint).where(
            RoleConstraint.constraint_type == "SSD",
            (RoleConstraint.tenant_id == tenant_id)
            | (RoleConstraint.tenant_id.is_(None)),
        )
        result = await db.execute(stmt)
        constraints = result.scalars().all()

        role_set = set(role_ids)
        for c in constraints:
            if c.role_id_1 in role_set and c.role_id_2 in role_set:
                return f"Conflict detected: Role {c.role_id_1} and Role {c.role_id_2} cannot be assigned together (SSD: {c.name})"

        return None
