"""系统设置端点 — 纯 HTTP 适配层"""

from typing import Any

from fastapi import APIRouter, Depends

from app.base.exceptions import ValidationError
from app.routers.deps import SettingsServiceDep, get_platform_admin
from app.schemas.admin import DynamicSettings

router = APIRouter()


@router.get("", response_model=DynamicSettings)
async def get_settings(
    service: SettingsServiceDep,
    _admin=Depends(get_platform_admin),
):
    """获取全站动态配置"""
    return await service.get_all()


@router.put("", response_model=DynamicSettings)
async def update_settings(
    data: dict[str, Any],
    service: SettingsServiceDep,
    _admin=Depends(get_platform_admin),
):
    """批量更新配置"""
    try:
        current = await service.get_all()
        current_dict = current.model_dump()
        current_dict.update(data)
        return await service.update(current_dict)
    except Exception as e:
        raise ValidationError(f"Invalid settings format: {str(e)}")
