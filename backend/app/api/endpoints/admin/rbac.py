from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_org, check_permission
from app.db.models import Role, Permission
from app.schemas.rbac import RoleRead, PermissionRead

router = APIRouter()


@router.get("/", response_model=List[RoleRead])
async def list_roles(
    org_id: int = Depends(get_current_org),
    _org_user=Depends(check_permission("org:manage_members")),
    db: AsyncSession = Depends(get_db),
):
    """获取组织的所有角色（包括系统角色和组织自定义角色）"""
    stmt = (
        select(Role)
        .options(selectinload(Role.permissions))
        .where((Role.org_id == org_id) | (Role.org_id.is_(None)))
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/permissions", response_model=List[PermissionRead])
async def list_permissions(
    _org_user=Depends(check_permission("org:manage_members")),
    db: AsyncSession = Depends(get_db),
):
    """获取所有可用权限"""
    stmt = select(Permission)
    result = await db.execute(stmt)
    return result.scalars().all()
