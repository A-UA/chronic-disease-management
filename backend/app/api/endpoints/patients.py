from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_org, get_current_user, get_db, check_permission
from app.db.models import User, PatientProfile
from app.schemas.patient import PatientProfileRead, PatientProfileUpdate

router = APIRouter()

# --- Helper ---
async def _load_patient_profile(db: AsyncSession, user_id: int, org_id: int) -> PatientProfile | None:
    stmt = select(PatientProfile).where(
        PatientProfile.user_id == user_id,
        PatientProfile.org_id == org_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

# --- Unified Endpoints ---

@router.get("/", response_model=List[PatientProfileRead])
async def list_patients(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    org_id: int = Depends(get_current_org),
    _permission=Depends(check_permission("patient:read")),
    db: AsyncSession = Depends(get_db),
):
    """[管理视图] 列出当前机构下的所有患者"""
    stmt = select(PatientProfile).where(PatientProfile.org_id == org_id)
    if search:
        stmt = stmt.where(PatientProfile.real_name.ilike(f"%{search}%"))
    stmt = stmt.offset(skip).limit(limit).order_by(PatientProfile.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/me", response_model=PatientProfileRead)
async def get_my_patient_profile(
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """[个人视图] 获取当前用户自己的患者档案"""
    profile = await _load_patient_profile(db, current_user.id, org_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return profile

@router.get("/{patient_id}", response_model=PatientProfileRead)
async def get_patient_detail(
    patient_id: int,
    org_id: int = Depends(get_current_org),
    _permission=Depends(check_permission("patient:read")),
    db: AsyncSession = Depends(get_db),
):
    """[管理视图] 获取特定患者详情"""
    patient = await db.get(PatientProfile, patient_id)
    if not patient or patient.org_id != org_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@router.put("/me", response_model=PatientProfileRead)
async def update_my_patient_profile(
    profile_in: PatientProfileUpdate,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """[个人视图] 更新当前用户自己的患者档案"""
    profile = await _load_patient_profile(db, current_user.id, org_id)
    if not profile:
        profile = PatientProfile(user_id=current_user.id, org_id=org_id, real_name="Unnamed")
        db.add(profile)
    
    for field, value in profile_in.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile

@router.put("/{patient_id}", response_model=PatientProfileRead)
async def admin_update_patient(
    patient_id: int,
    profile_in: PatientProfileUpdate,
    org_id: int = Depends(get_current_org),
    _permission=Depends(check_permission("patient:update")),
    db: AsyncSession = Depends(get_db),
):
    """[管理视图] 管理员修改患者信息"""
    patient = await db.get(PatientProfile, patient_id)
    if not patient or patient.org_id != org_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    for field, value in profile_in.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    await db.commit()
    await db.refresh(patient)
    return patient
