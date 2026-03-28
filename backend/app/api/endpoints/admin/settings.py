from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List

from app.api.deps import get_db, get_platform_admin
from app.schemas.admin import SystemSettingRead, SystemSettingUpdate

router = APIRouter()


@router.get("/", response_model=List[SystemSettingRead])
async def get_settings(
    _admin=Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT key, value, description FROM system_settings")
    )
    return [
        SystemSettingRead(key=r.key, value=r.value, description=r.description)
        for r in result.all()
    ]


@router.put("/{key}")
async def update_setting(
    key: str,
    data: SystemSettingUpdate,
    _admin=Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT key FROM system_settings WHERE key = :key"), {"key": key}
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Setting not found")

    await db.execute(
        text("UPDATE system_settings SET value = :value WHERE key = :key"),
        {"key": key, "value": data.value},
    )
    await db.commit()
    return {"status": "ok"}
