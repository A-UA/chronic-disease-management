from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user, check_permission, get_current_org
from app.db.models import Organization, OrganizationUser, User, Role
from app.schemas.organization import (
    OrganizationReadAdmin, 
    OrganizationCreate, 
    OrganizationUpdate,
    OrganizationMemberRead
)

router = APIRouter()

@router.get("/me", response_model=List[OrganizationReadAdmin])
async def get_my_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """[通用] 获取当前用户所属的所有机构"""
    stmt = (
        select(Organization)
        .join(OrganizationUser)
        .where(OrganizationUser.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/", response_model=List[OrganizationReadAdmin])
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    _permission=Depends(check_permission("platform:manage")), # 仅限平台级角色
    db: AsyncSession = Depends(get_db)
):
    """[管理视图] 列出系统所有机构"""
    stmt = select(Organization).offset(skip).limit(limit)
    if search:
        stmt = stmt.where(Organization.name.ilike(f"%{search}%"))
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=OrganizationReadAdmin)
async def create_organization(
    org_in: OrganizationCreate,
    _permission=Depends(check_permission("platform:manage")),
    db: AsyncSession = Depends(get_db)
):
    """[管理视图] 创建新机构"""
    org = Organization(name=org_in.name, plan_type=org_in.plan_type)
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org

@router.get("/{org_id}/members", response_model=List[OrganizationMemberRead])
async def get_organization_members(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """[管理视图] 获取机构成员列表 (含角色)"""
    # 校验是否是该机构成员或平台管理员
    stmt_check = select(OrganizationUser).where(
        OrganizationUser.org_id == org_id,
        OrganizationUser.user_id == current_user.id
    )
    if not (await db.execute(stmt_check)).scalar_one_or_none() and current_user.role_code != "platform_admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    stmt = (
        select(OrganizationUser)
        .options(
            selectinload(OrganizationUser.user),
            selectinload(OrganizationUser.rbac_roles).selectinload(Role.permissions)
        )
        .where(OrganizationUser.org_id == org_id)
    )
    result = await db.execute(stmt)
    members = []
    for org_user in result.scalars().all():
        members.append({
            "user_id": org_user.user.id,
            "email": org_user.user.email,
            "name": org_user.user.name,
            "roles": [r.code for r in org_user.rbac_roles],
            "user_type": org_user.user_type,
        })
    return members
