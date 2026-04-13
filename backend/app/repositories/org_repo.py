from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Organization, OrganizationUser, Role
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Organization)

    async def list_user_orgs(self, user_id: int) -> list[Organization]:
        stmt = (
            select(self.model)
            .join(OrganizationUser)
            .where(OrganizationUser.user_id == user_id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_by_tenant(
        self, tenant_id: int, search: str | None = None, skip: int = 0, limit: int = 100
    ) -> tuple[int, list[Organization]]:
        base = select(self.model).where(self.model.tenant_id == tenant_id)
        if search:
            base = base.where(
                self.model.name.ilike(f"%{search}%") | self.model.code.ilike(f"%{search}%")
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = base.order_by(self.model.sort, self.model.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())

    async def check_code_exists(self, tenant_id: int, code: str) -> bool:
        stmt = select(self.model).where(
            self.model.tenant_id == tenant_id, self.model.code == code
        )
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def get_members_with_roles(self, org_id: int) -> list[OrganizationUser]:
        stmt = (
            select(OrganizationUser)
            .options(
                selectinload(OrganizationUser.user),
                selectinload(OrganizationUser.rbac_roles).selectinload(Role.permissions),
            )
            .where(OrganizationUser.org_id == org_id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

