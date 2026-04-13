from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrganizationInvitation
from app.repositories.base import BaseRepository


class OrganizationInvitationRepository(BaseRepository[OrganizationInvitation]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, OrganizationInvitation)

    async def list_pending(self, org_id: int) -> list[OrganizationInvitation]:
        stmt = select(self.model).where(
            self.model.org_id == org_id, self.model.status == "pending"
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_by_token(self, token: str) -> OrganizationInvitation | None:
        stmt = select(self.model).where(
            self.model.token == token, self.model.status == "pending"
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
