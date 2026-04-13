"""SettingsService 实例化适配器 — 包装静态 SettingsService 以适配 ServiceDep"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.admin import DynamicSettings
from app.services.system.settings import SettingsService as StaticSettingsService


class SettingsServiceAdapter:
    """将静态方法的 SettingsService 包装为实例化的 Service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> DynamicSettings:
        return await StaticSettingsService.get_all(self.db)

    async def update(self, new_settings: dict[str, Any]) -> DynamicSettings:
        return await StaticSettingsService.update(self.db, new_settings)
