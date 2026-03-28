from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import check_permission, get_current_org, get_current_user, get_db
from app.db.models import Role, User, Organization, OrganizationUser, PatientProfile, PatientManagerAssignment
from app.schemas.organization import OrganizationReadAdmin, OrganizationMemberRead, PatientAssignmentCreate

router = APIRouter()

@router.post("/{org_id}/assignments", response_model=dict)
async def assign_patient_to_manager(
    org_id: int,
    assign_in: PatientAssignmentCreate,
    current_org_id: int = Depends(get_current_org),
    _org_user: OrganizationUser = Depends(check_permission("org:manage_members")),
    db: AsyncSession = Depends(get_db)
) -> Any:
    if current_org_id != org_id:
        raise HTTPException(status_code=403, detail="Organization context mismatch")

    stmt_p = select(PatientProfile).where(
        PatientProfile.id == assign_in.patient_id,
        PatientProfile.org_id == org_id
    )
    res_p = await db.execute(stmt_p)
    if not res_p.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found in this organization")

    stmt_m = select(OrganizationUser).where(
        OrganizationUser.org_id == org_id,
        OrganizationUser.user_id == assign_in.manager_id,
        OrganizationUser.user_type == "staff"
    )
    res_m = await db.execute(stmt_m)
    if not res_m.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Manager not found in this organization")

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
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt_check = select(OrganizationUser).where(
        OrganizationUser.org_id == org_id,
        OrganizationUser.user_id == current_user.id
    )
    res_check = await db.execute(stmt_check)
    if not res_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

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
        role_codes = sorted(role.code for role in org_user.rbac_roles)
        members.append({
            "user_id": org_user.user.id,
            "email": org_user.user.email,
            "name": org_user.user.name,
            "roles": role_codes,
            "user_type": org_user.user_type,
        })
    return members
