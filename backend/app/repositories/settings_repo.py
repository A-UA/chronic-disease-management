from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SystemSetting
from app.repositories.base import BaseRepository


class SettingsRepository(BaseRepository[SystemSetting]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, SystemSetting)

    async def get_by_key(self, key: str) -> SystemSetting | None:
        stmt = select(self.model).where(self.model.key == key)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_all_settings(self) -> list[SystemSetting]:
        stmt = select(self.model)
        return list((await self.db.execute(stmt)).scalars().all())
