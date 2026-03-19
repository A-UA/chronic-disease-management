from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models import User, Organization, OrganizationUser, PatientProfile, PatientManagerAssignment
from app.schemas.organization import OrganizationReadAdmin, OrganizationMemberRead, PatientAssignmentCreate

router = APIRouter()

@router.post("/{org_id}/assignments", response_model=dict)
async def assign_patient_to_manager(
    org_id: UUID,
    assign_in: PatientAssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    行政管理功能：管理员将患者指派给特定管理师。
    """
    # 1. 校验当前用户是否为该组织的管理员
    stmt = select(OrganizationUser).where(
        OrganizationUser.org_id == org_id,
        OrganizationUser.user_id == current_user.id,
        OrganizationUser.role.in_(["owner", "admin"])
    )
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Only admins can assign patients")
        
    # 2. 校验患者是否属于该组织
    stmt_p = select(PatientProfile).where(
        PatientProfile.id == assign_in.patient_id,
        PatientProfile.org_id == org_id
    )
    res_p = await db.execute(stmt_p)
    if not res_p.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found in this organization")

    # 3. 创建或更新分配关系
    from sqlalchemy.dialects.postgresql import insert
    stmt_ins = insert(PatientManagerAssignment).values(
        org_id=org_id,
        manager_id=assign_in.manager_id,
        patient_id=assign_in.patient_id,
        assignment_role=assign_in.role
    ).on_conflict_do_update(
        index_elements=['manager_id', 'patient_id'],
        set_={'assignment_role': assign_in.role}
    )
    await db.execute(stmt_ins)
    await db.commit()
    return {"status": "success", "message": "Patient assigned successfully"}

@router.get("/me", response_model=List[OrganizationReadAdmin])
async def get_my_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取当前用户所属的所有组织（作为成员或所有者）。
    """
    stmt = (
        select(Organization)
        .join(OrganizationUser)
        .where(OrganizationUser.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{org_id}/members", response_model=List[OrganizationMemberRead])
async def get_organization_members(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取组织的成员列表（仅限组织成员查看）。
    """
    # 1. 校验当前用户是否属于该组织
    stmt_check = select(OrganizationUser).where(
        OrganizationUser.org_id == org_id,
        OrganizationUser.user_id == current_user.id
    )
    res_check = await db.execute(stmt_check)
    if not res_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    # 2. 获取成员详情并脱敏映射
    stmt = (
        select(User.id, User.email, User.name, OrganizationUser.role)
        .join(OrganizationUser, OrganizationUser.user_id == User.id)
        .where(OrganizationUser.org_id == org_id)
    )
    result = await db.execute(stmt)
    members = []
    for row in result.all():
        members.append({
            "user_id": row[0],
            "email": row[1],
            "name": row[2],
            "role": row[3]
        })
    return members
