"""系统设置服务适配器，接入依赖注入系统"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.models import SystemSetting
from app.repositories.settings_repo import SettingsRepository
from app.schemas.admin import DynamicSettings


class SettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SettingsRepository(db)

    async def get_all(self) -> DynamicSettings:
        """获取所有系统设置"""
        settings_list = await self.repo.list_all_settings()
        settings_dict = {s.key: s.value for s in settings_list}
        
        # 转换对应的数据类型，否则默认是 pydantic default
        parsed = {}
        for k, v in settings_dict.items():
            if v.lower() in ("true", "false"):
                parsed[k] = v.lower() == "true"
            elif v.isdigit():
                parsed[k] = int(v)
            else:
                try:
                    parsed[k] = float(v)
                except ValueError:
                    parsed[k] = v
                    
        return DynamicSettings(**parsed)

    async def update(self, data: dict[str, Any]) -> DynamicSettings:
        """批量更新系统设置"""
        for key, value in data.items():
            val_str = str(value).lower() if isinstance(value, bool) else str(value)
            setting = await self.repo.get_by_key(key)
            if setting:
                await self.repo.update(setting, {"value": val_str})
            else:
                new_setting = SystemSetting(key=key, value=val_str, description="")
                await self.repo.create(new_setting)

        await self.db.commit()
        return await self.get_all()
