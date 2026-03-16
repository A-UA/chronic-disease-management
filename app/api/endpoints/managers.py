from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.api.deps import get_db, get_current_user, get_current_org
from app.db.models import User, PatientProfile, PatientManagerAssignment, ManagementSuggestion
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter()

class PatientShortRead(BaseModel):
    id: UUID
    real_name: str
    gender: str | None
    
    model_config = ConfigDict(from_attributes=True)

class SuggestionCreate(BaseModel):
    content: str
    suggestion_type: str = "general"

class SuggestionRead(BaseModel):
    id: UUID
    manager_id: UUID
    patient_id: UUID
    content: str
    suggestion_type: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

from app.db.models import User, PatientProfile, PatientManagerAssignment, ManagementSuggestion, OrganizationUser

@router.get("/patients", response_model=List[PatientShortRead])
async def get_assigned_patients(
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # 1. 检查当前用户的 RBAC 角色
    stmt_role = select(OrganizationUser).where(
        OrganizationUser.org_id == org_id,
        OrganizationUser.user_id == current_user.id
    )
    res_role = await db.execute(stmt_role)
    org_user = res_role.scalar_one_or_none()
    
    is_admin = org_user and org_user.role in ["owner", "admin"]

    # 2. 如果是管理员，返回全机构患者；如果是普通成员，只返回分配的患者
    if is_admin:
        stmt = select(PatientProfile).where(PatientProfile.org_id == org_id)
    else:
        stmt = select(PatientProfile).join(
            PatientManagerAssignment, 
            PatientManagerAssignment.patient_id == PatientProfile.id
        ).where(
            PatientManagerAssignment.manager_id == current_user.id,
            PatientProfile.org_id == org_id
        )
        
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/patients/{patient_id}/suggestions", response_model=SuggestionRead)
async def create_suggestion(
    patient_id: UUID,
    suggestion_in: SuggestionCreate,
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # 1. 检查 RBAC 角色
    stmt_role = select(OrganizationUser).where(
        OrganizationUser.org_id == org_id,
        OrganizationUser.user_id == current_user.id
    )
    res_role = await db.execute(stmt_role)
    org_user = res_role.scalar_one_or_none()
    is_admin = org_user and org_user.role in ["owner", "admin"]

    # 2. 如果不是管理员，校验是否分配了该患者
    if not is_admin:
        stmt = select(PatientManagerAssignment).where(
            PatientManagerAssignment.manager_id == current_user.id,
            PatientManagerAssignment.patient_id == patient_id
        )
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not authorized to manage this patient")
        
    # 3. 校验患者是否属于该机构 (即使是管理员，也要受 RLS 之外的逻辑一致性保护)
    stmt_p = select(PatientProfile).where(
        PatientProfile.id == patient_id,
        PatientProfile.org_id == org_id
    )
    res_p = await db.execute(stmt_p)
    if not res_p.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found in this organization")

    # 4. 创建建议
    suggestion = ManagementSuggestion(
        org_id=org_id,
        manager_id=current_user.id,
        patient_id=patient_id,
        content=suggestion_in.content,
        suggestion_type=suggestion_in.suggestion_type
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)
    return suggestion

@router.get("/patients/{patient_id}/suggestions", response_model=List[SuggestionRead])
async def get_patient_suggestions(
    patient_id: UUID,
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # 1. Verify access (manager must be assigned to patient OR be an admin in org)
    # For now, strict manager-patient assignment check
    stmt_check = select(PatientManagerAssignment).where(
        PatientManagerAssignment.manager_id == current_user.id,
        PatientManagerAssignment.patient_id == patient_id
    )
    res_check = await db.execute(stmt_check)
    if not res_check.scalar_one_or_none():
         raise HTTPException(status_code=403, detail="Not authorized to view this patient's suggestions")

    # 2. Get suggestions
    stmt = select(ManagementSuggestion).where(
        ManagementSuggestion.patient_id == patient_id,
        ManagementSuggestion.org_id == org_id
    ).order_by(ManagementSuggestion.created_at.desc())
    
    result = await db.execute(stmt)
    return result.scalars().all()
