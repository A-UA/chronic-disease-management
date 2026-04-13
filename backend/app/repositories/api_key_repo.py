from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey
from app.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ApiKey)

    async def list_by_org(self, org_id: int, skip: int = 0, limit: int = 50) -> list[ApiKey]:
        stmt = (
            select(self.model)
            .where(self.model.org_id == org_id)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def increment_token_usage(self, api_key_id: int, tokens: int) -> None:
        from sqlalchemy import update
        stmt = (
            update(self.model)
            .where(self.model.id == api_key_id)
            .values(token_used=self.model.token_used + tokens)
        )
        await self.db.execute(stmt)
