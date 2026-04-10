import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import SystemSetting
from app.schemas.admin import DynamicSettings
from app.services.system.quota import redis_client

logger = logging.getLogger(__name__)

CACHE_KEY = "system_dynamic_settings"
CACHE_TTL = 300  # 5 minutes


class SettingsService:
    @staticmethod
    async def get_all(db: AsyncSession) -> DynamicSettings:
        """获取所有动态设置，优先走缓存"""
        # 1. Try Cache
        cached = await redis_client.get(CACHE_KEY)
        if cached:
            try:
                return DynamicSettings.model_validate_json(cached)
            except Exception:
                logger.warning("Failed to parse cached settings")

        # 2. Query DB
        stmt = select(SystemSetting)
        res = await db.execute(stmt)
        rows = res.scalars().all()

        db_data = {row.key: row.value for row in rows}

        # 3. Merge with Code Defaults
        # We parse the DB string values into their proper types via Pydantic
        # Handle cases where DB might have strings for bool/int
        typed_data = {}
        for key, value in db_data.items():
            if value.lower() == "true":
                typed_data[key] = True
            elif value.lower() == "false":
                typed_data[key] = False
            else:
                try:
                    # Try numeric
                    if "." in value:
                        typed_data[key] = float(value)
                    else:
                        typed_data[key] = int(value)
                except ValueError:
                    typed_data[key] = value

        # Create instance (missing fields will use default values from Pydantic class)
        settings_obj = DynamicSettings(**typed_data)

        # 4. Save to Cache
        await redis_client.setex(CACHE_KEY, CACHE_TTL, settings_obj.model_dump_json())

        return settings_obj

    @staticmethod
    async def update(db: AsyncSession, new_settings: dict[str, Any]) -> DynamicSettings:
        """更新设置并失效缓存"""
        # Validate first
        validated = DynamicSettings(**new_settings)
        data_to_save = validated.model_dump()

        for key, value in data_to_save.items():
            # Standard string storage
            str_value = str(value).lower() if isinstance(value, bool) else str(value)

            # Upsert logic (SQLAlchemy 2.0 style)
            # Since key is primary key, we check existence
            stmt = select(SystemSetting).where(SystemSetting.key == key)
            existing = (await db.execute(stmt)).scalar_one_or_none()

            if existing:
                existing.value = str_value
            else:
                db.add(SystemSetting(key=key, value=str_value))

        await db.commit()

        # Invalidate Cache
        await redis_client.delete(CACHE_KEY)

        return validated


async def get_system_settings(db: AsyncSession) -> DynamicSettings:
    """快捷工具函数"""
    return await SettingsService.get_all(db)
