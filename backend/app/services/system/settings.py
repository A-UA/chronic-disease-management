"""系统设置服务适配器，接入依赖注入系统"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import NotFoundError
from app.models import SystemSettings
from app.repositories.settings_repo import SettingsRepository


class SettingsServiceAdapter:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SettingsRepository(db)

    async def get_all_settings(self) -> dict[str, str]:
        """获取所有系统设置"""
        settings_list = await self.repo.list_all_settings()
        return {s.key: s.value for s in settings_list}

    async def update_settings(self, data: dict[str, str]) -> dict[str, str]:
        """批量更新系统设置"""
        for key, value in data.items():
            setting = await self.repo.get_by_key(key)
            if setting:
                await self.repo.update(setting, {"value": value})
            else:
                new_setting = SystemSettings(key=key, value=value, description="")
                await self.repo.create(new_setting)
        
        await self.db.commit()
        return await self.get_all_settings()
