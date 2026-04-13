from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrganizationUser, OrganizationUserRole
from app.repositories.base import BaseRepository


class OrganizationUserRepository(BaseRepository[OrganizationUser]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, OrganizationUser)

    async def get_by_org_and_user(self, org_id: int, user_id: int) -> OrganizationUser | None:
        from sqlalchemy import select
        stmt = select(self.model).where(self.model.org_id == org_id, self.model.user_id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

class OrganizationUserRoleRepository(BaseRepository[OrganizationUserRole]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, OrganizationUserRole)
