from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.api.deps import get_db, get_current_user, get_current_org
from app.db.models import User, PatientProfile, PatientManagerAssignment, ManagementSuggestion
from pydantic import BaseModel, ConfigDict

router = APIRouter()

class PatientBriefRead(BaseModel):
    id: UUID
    user_id: UUID
    real_name: str
    gender: str | None = None
    
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
    created_at: Any
    
    model_config = ConfigDict(from_attributes=True)

@router.get("/patients", response_model=List[PatientBriefRead])
async def get_my_assigned_patients(
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    管理师查看分配给自己的患者列表。
    """
    stmt = (
        select(PatientProfile)
        .join(PatientManagerAssignment, PatientProfile.id == PatientManagerAssignment.patient_id)
        .where(
            PatientManagerAssignment.manager_id == current_user.id,
            PatientManagerAssignment.org_id == org_id
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/patients/{patient_id}/suggestions", response_model=SuggestionRead)
async def create_patient_suggestion(
    patient_id: UUID,
    suggest_in: SuggestionCreate,
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # 1. 校验分配关系
    stmt = select(PatientManagerAssignment).where(
        PatientManagerAssignment.manager_id == current_user.id,
        PatientManagerAssignment.patient_id == patient_id,
        PatientManagerAssignment.org_id == org_id
    )
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not assigned to this patient")

    # 2. 创建建议
    suggestion = ManagementSuggestion(
        org_id=org_id,
        manager_id=current_user.id,
        patient_id=patient_id,
        content=suggest_in.content,
        suggestion_type=suggest_in.suggestion_type
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)
    return suggestion

@router.get("/patients/{patient_id}/suggestions", response_model=List[SuggestionRead])
async def get_patient_suggestion_history(
    patient_id: UUID,
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # 1. 校验权限
    stmt_check = select(PatientManagerAssignment).where(
        PatientManagerAssignment.manager_id == current_user.id,
        PatientManagerAssignment.patient_id == patient_id,
        PatientManagerAssignment.org_id == org_id
    )
    res_check = await db.execute(stmt_check)
    if not res_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized to view this patient's history")

    # 2. 获取历史
    stmt = select(ManagementSuggestion).where(
        ManagementSuggestion.patient_id == patient_id,
        ManagementSuggestion.org_id == org_id
    ).order_by(ManagementSuggestion.created_at.desc())
    
    result = await db.execute(stmt)
    return result.scalars().all()
