from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrganizationUser, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def list_by_tenant(
        self, tenant_id: int, search: str | None = None, skip: int = 0, limit: int = 50
    ) -> tuple[int, list[User]]:
        base = (
            select(self.model)
            .join(OrganizationUser, OrganizationUser.user_id == self.model.id)
            .where(OrganizationUser.tenant_id == tenant_id)
            .distinct()
        )
        if search:
            base = base.where(
                self.model.email.ilike(f"%{search}%") | self.model.name.ilike(f"%{search}%")
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = base.order_by(self.model.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())

    async def get_by_email(self, email: str, exclude_id: int | None = None) -> User | None:
        stmt = select(self.model).where(self.model.email == email)
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
