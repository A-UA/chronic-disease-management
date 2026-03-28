from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.api.deps import get_db, get_current_org, check_permission
from app.db.models import PatientProfile
from app.schemas.patient import PatientProfileRead

router = APIRouter()


@router.get("/", response_model=List[PatientProfileRead])
async def list_patients(
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    org_id: int = Depends(get_current_org),
    _org_user=Depends(check_permission("patient:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PatientProfile).where(PatientProfile.org_id == org_id)
    if search:
        stmt = stmt.where(PatientProfile.real_name.ilike(f"%{search}%"))
    stmt = stmt.offset(skip).limit(limit).order_by(PatientProfile.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{patient_id}", response_model=PatientProfileRead)
async def get_patient(
    patient_id: int,
    org_id: int = Depends(get_current_org),
    _org_user=Depends(check_permission("patient:view")),
    db: AsyncSession = Depends(get_db),
):
    patient = await db.get(PatientProfile, patient_id)
    if not patient or patient.org_id != org_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/{patient_id}")
async def update_patient(
    patient_id: int,
    real_name: str | None = None,
    gender: str | None = None,
    org_id: int = Depends(get_current_org),
    _org_user=Depends(check_permission("patient:edit")),
    db: AsyncSession = Depends(get_db),
):
    patient = await db.get(PatientProfile, patient_id)
    if not patient or patient.org_id != org_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    if real_name is not None:
        patient.real_name = real_name
    if gender is not None:
        patient.gender = gender
    await db.commit()
    return {"status": "ok"}
