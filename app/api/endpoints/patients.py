from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.api.deps import get_db, get_current_user, get_current_org
from app.db.models import User, PatientProfile
from pydantic import BaseModel, ConfigDict
from datetime import date

router = APIRouter()

class PatientProfileUpdate(BaseModel):
    real_name: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    medical_history: dict | None = None

class PatientProfileRead(BaseModel):
    id: UUID
    user_id: UUID
    org_id: UUID
    real_name: str
    gender: str | None
    birth_date: date | None
    medical_history: dict | None
    
    model_config = ConfigDict(from_attributes=True)

@router.get("/me", response_model=PatientProfileRead)
async def get_my_patient_profile(
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(PatientProfile).where(
        PatientProfile.user_id == current_user.id,
        PatientProfile.org_id == org_id
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found in this organization")
    return profile

@router.put("/me", response_model=PatientProfileRead)
async def update_my_patient_profile(
    profile_in: PatientProfileUpdate,
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(PatientProfile).where(
        PatientProfile.user_id == current_user.id,
        PatientProfile.org_id == org_id
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create profile if it doesn't exist? 
        # For simplicity, we assume registration created a default profile or user must be added to org as patient first.
        # But our current registration creates Org but not PatientProfile.
        # Let's allow creation if not exists.
        profile = PatientProfile(
            user_id=current_user.id,
            org_id=org_id,
            real_name=profile_in.real_name or current_user.name or "Unnamed Patient"
        )
        db.add(profile)
    
    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    await db.commit()
    await db.refresh(profile)
    return profile
