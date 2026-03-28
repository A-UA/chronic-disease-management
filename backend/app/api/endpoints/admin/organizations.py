from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import check_permission, get_current_org, get_current_user, get_db, get_platform_admin, get_platform_viewer
from app.db.models import Role, User, Organization, OrganizationUser, PatientProfile, PatientManagerAssignment
from app.schemas.organization import OrganizationReadAdmin, OrganizationMemberRead, PatientAssignmentCreate, OrganizationCreate, OrganizationUpdate

router = APIRouter()

@router.get("/", response_model=List[OrganizationReadAdmin])
async def list_all_organizations(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    _admin=Depends(get_platform_viewer),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    [平台管理员] 列出系统中所有的组织
    """
    stmt = select(Organization).offset(skip).limit(limit)
    if search:
        stmt = stmt.where(Organization.name.ilike(f"%{search}%"))
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=OrganizationReadAdmin)
async def create_organization(
    org_in: OrganizationCreate,
    _admin=Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    [平台管理员] 手动创建一个新组织
    """
    org = Organization(name=org_in.name, plan_type=org_in.plan_type)
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org

@router.put("/{org_id}", response_model=OrganizationReadAdmin)
async def update_organization(
    org_id: int,
    org_in: OrganizationUpdate,
    _admin=Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    [平台管理员] 修改组织信息或调整配额
    """
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if org_in.name is not None:
        org.name = org_in.name
    if org_in.plan_type is not None:
        org.plan_type = org_in.plan_type
    if org_in.quota_tokens_limit is not None:
        org.quota_tokens_limit = org_in.quota_tokens_limit
        
    await db.commit()
    await db.refresh(org)
    return org

@router.delete("/{org_id}")
async def delete_organization(
    org_id: int,
    _admin=Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    [平台管理员] 删除组织
    """
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    await db.delete(org)
    await db.commit()
    return {"status": "success"}

@router.post("/{org_id}/assignments", response_model=dict)
async def assign_patient_to_manager(
    org_id: int,
    assign_in: PatientAssignmentCreate,
    current_org_id: int = Depends(get_current_org),
    _org_user: OrganizationUser = Depends(check_permission("org:manage_members")),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # Existing logic remains...
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
