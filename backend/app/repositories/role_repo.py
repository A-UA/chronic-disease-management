from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Role, Permission, RoleConstraint
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Role)

    async def get_staff_role(self, tenant_id: int) -> Role | None:
        stmt = select(self.model).where(
            self.model.code == "staff",
            (self.model.tenant_id == tenant_id) | (self.model.tenant_id.is_(None)),
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_roles_with_perms(self, tenant_id: int, org_id: int, search: str | None = None, skip: int = 0, limit: int = 50) -> tuple[int, list[Role]]:
        base = select(self.model).where(
            (self.model.tenant_id == tenant_id) & (self.model.org_id == org_id) | (self.model.tenant_id.is_(None))
        )
        if search:
            base = base.where(self.model.name.ilike(f"%{search}%") | self.model.code.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = base.options(selectinload(self.model.permissions)).offset(skip).limit(limit).order_by(self.model.id)
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())

    async def get_role_with_perms(self, role_id: int, tenant_id: int, org_id: int) -> Role | None:
        stmt = select(self.model).options(selectinload(self.model.permissions)).where(
            self.model.id == role_id,
            (self.model.tenant_id == tenant_id) & (self.model.org_id == org_id) | (self.model.tenant_id.is_(None))
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def check_code_exists(self, code: str, tenant_id: int, org_id: int, exclude_id: int | None = None) -> bool:
        stmt = select(self.model).where(
            self.model.code == code, self.model.tenant_id == tenant_id, self.model.org_id == org_id
        )
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Permission)

    async def list_all(self) -> list[Permission]:
        stmt = select(self.model)
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_perms_by_codes(self, codes: list[str]) -> list[Permission]:
        stmt = select(self.model).where(self.model.code.in_(codes))
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_codes_by_role_ids(self, role_ids: list[int]) -> set[str]:
        stmt = (
            select(self.model.code)
            .join(self.model.roles)
            .where(Role.id.in_(role_ids))
            .distinct()
        )
        return {row[0] for row in (await self.db.execute(stmt)).all()}

    async def get_all_role_ids(self, direct_role_ids: list[int]) -> set[int]:
        from sqlalchemy import text
        if not direct_role_ids:
            return set()
        query = text("""
            WITH RECURSIVE role_hierarchy AS (
                SELECT id, parent_role_id
                FROM roles
                WHERE id = ANY(:role_ids)
                UNION
                SELECT r.id, r.parent_role_id
                FROM roles r
                INNER JOIN role_hierarchy rh ON rh.parent_role_id = r.id
            )
            SELECT id FROM role_hierarchy;
        """)
        result = await self.db.execute(query, {"role_ids": direct_role_ids})
        return {row[0] for row in result.fetchall()}

class RoleConstraintRepository(BaseRepository[RoleConstraint]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, RoleConstraint)

    async def get_ssd_constraints(self, tenant_id: int | None) -> list[RoleConstraint]:
        stmt = select(self.model).where(
            self.model.constraint_type == "SSD",
            (self.model.tenant_id == tenant_id) | (self.model.tenant_id.is_(None)),
        )
        return list((await self.db.execute(stmt)).scalars().all())

from app.models.rbac import Resource, Action

class ResourceRepository(BaseRepository[Resource]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Resource)
        
    async def list_all(self):
        return list((await self.db.execute(select(self.model))).scalars().all())

class ActionRepository(BaseRepository[Action]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Action)

    async def list_all(self):
        return list((await self.db.execute(select(self.model))).scalars().all())
