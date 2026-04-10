from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.deps import get_db, get_platform_admin
from app.schemas.admin import DynamicSettings
from app.services.system.settings import SettingsService

router = APIRouter()


@router.get("", response_model=DynamicSettings)
async def get_settings(
    _admin=Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取全站动态配置"""
    return await SettingsService.get_all(db)


@router.put("", response_model=DynamicSettings)
async def update_settings(
    data: dict[str, Any],
    _admin=Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量更新配置（支持部分更新）"""
    try:
        # 获取当前所有设置
        current = await SettingsService.get_all(db)
        current_dict = current.model_dump()

        # 合并新旧值
        current_dict.update(data)

        # 使用服务进行校验并保存
        updated = await SettingsService.update(db, current_dict)
        return updated
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid settings format: {str(e)}"
        )
