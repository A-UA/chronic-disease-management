from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_org, get_current_user, get_db
from app.db.models import User, PatientProfile
from app.schemas.patient import PatientProfileRead, PatientProfileUpdate

router = APIRouter()

async def _load_patient_profile(db: AsyncSession, user_id: int, org_id: int) -> PatientProfile | None:
    stmt = select(PatientProfile).where(
        PatientProfile.user_id == user_id,
        PatientProfile.org_id == org_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


@router.get("/me", response_model=PatientProfileRead)
async def get_my_patient_profile(
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    profile = await _load_patient_profile(db, current_user.id, org_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return profile


@router.put("/me", response_model=PatientProfileRead)
async def update_my_patient_profile(
    profile_in: PatientProfileUpdate,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    profile = await _load_patient_profile(db, current_user.id, org_id)
    
    if not profile:
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
