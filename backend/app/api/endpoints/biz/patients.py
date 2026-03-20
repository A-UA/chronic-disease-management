from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.api.deps import get_db, get_current_user, get_current_org
from app.db.models import User, PatientProfile
from app.schemas.patient import PatientProfileRead, PatientProfileUpdate
from datetime import date

from app.api.deps import get_db, get_current_user, get_current_org, require_patient_identity
...
@router.get("/me", response_model=PatientProfileRead)
async def get_my_patient_profile(
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    patient_id: UUID = Depends(require_patient_identity),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # Now we can just use the patient_id found by dependency
    profile = await db.get(PatientProfile, patient_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")
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
