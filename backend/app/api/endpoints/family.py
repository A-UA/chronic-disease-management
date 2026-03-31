from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.api.deps import get_db, get_current_user, get_current_org
from app.db.models import User, PatientFamilyLink, PatientProfile, ManagementSuggestion
from app.services.audit import audit_action
from pydantic import BaseModel, ConfigDict
from datetime import date

router = APIRouter()

class FamilyLinkCreate(BaseModel):
    patient_id: int
    family_user_email: str
    relationship_type: str | None = None
    access_level: int = 1

class FamilyLinkRead(BaseModel):
    patient_id: int
    family_user_id: int
    relationship_type: str | None
    access_level: int
    status: str
    
    model_config = ConfigDict(from_attributes=True)

class PatientProfileFamilyRead(BaseModel):
    id: int
    real_name: str
    gender: str | None
    birth_date: date | None
    medical_history: dict | None
    relationship_type: str | None
    
    model_config = ConfigDict(from_attributes=True)

@router.post("/links", response_model=FamilyLinkRead)
async def create_family_link(
    link_in: FamilyLinkCreate,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # 1. Verify patient belongs to current_user or current_user is admin in org
    # For now, we assume the patient creates the link for a family member.
    stmt = select(PatientProfile).where(
        PatientProfile.id == link_in.patient_id,
        PatientProfile.org_id == org_id,
        PatientProfile.user_id == current_user.id
    )
    result = await db.execute(stmt)
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=403, detail="Not authorized to link this patient")
        
    # 2. Find family user by email
    stmt_user = select(User).where(User.email == link_in.family_user_email)
    res_user = await db.execute(stmt_user)
    family_user = res_user.scalar_one_or_none()
    if not family_user:
        raise HTTPException(status_code=404, detail="Family user not found")
        
    # 3. Create link
    link = PatientFamilyLink(
        patient_id=link_in.patient_id,
        family_user_id=family_user.id,
        relationship_type=link_in.relationship_type,
        access_level=link_in.access_level,
        status="active" # In production, maybe "pending" until accepted
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link

@router.get("/patients", response_model=List[FamilyLinkRead])
async def get_my_linked_patients(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # As a family member, get all patients linked to me
    stmt = select(PatientFamilyLink).where(
        PatientFamilyLink.family_user_id == current_user.id,
        PatientFamilyLink.status == "active"
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/patients/{patient_id}", response_model=PatientProfileFamilyRead)
async def get_linked_patient_profile(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # 1. Verify link exists
    stmt = select(PatientFamilyLink).where(
        PatientFamilyLink.patient_id == patient_id,
        PatientFamilyLink.family_user_id == current_user.id,
        PatientFamilyLink.status == "active"
    )
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=403, detail="No active family link for this patient")
    
    # 2. Fetch patient profile
    # RLS will allow this because app.current_user_id is set in deps.get_current_user!
    stmt_p = select(PatientProfile).where(PatientProfile.id == patient_id)
    res_p = await db.execute(stmt_p)
    patient = res_p.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
        
    # Audit access
    await audit_action(
        db, 
        user_id=current_user.id, 
        org_id=patient.org_id, 
        action="view_patient_family", 
        resource_type="PatientProfile", 
        resource_id=patient.id
    )
    await db.commit() # Ensure audit log is saved
    
    # Combine with link info
    return {
        "id": patient.id,
        "real_name": patient.real_name,
        "gender": patient.gender,
        "birth_date": patient.birth_date,
        "medical_history": patient.medical_history,
        "relationship_type": link.relationship_type
    }
