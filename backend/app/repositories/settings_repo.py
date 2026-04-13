from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SystemSettings
from app.repositories.base import BaseRepository


class SettingsRepository(BaseRepository[SystemSettings]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, SystemSettings)

    async def get_by_key(self, key: str) -> SystemSettings | None:
        stmt = select(self.model).where(self.model.key == key)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_all_settings(self) -> list[SystemSettings]:
        stmt = select(self.model)
        return list((await self.db.execute(stmt)).scalars().all())
