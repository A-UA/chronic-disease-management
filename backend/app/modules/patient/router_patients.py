from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import (
    get_current_org_id, get_effective_org_id, get_current_user,
    get_current_tenant_id, get_db, check_permission, inject_rls_context,
)
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

@router.get("", response_model=List[PatientProfileRead])
async def list_patients(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("patient:read")),
    db: AsyncSession = Depends(get_db),
):
    """[管理视图] 列出患者
    - admin/owner: 看全租户（RLS 保证隔离）
    - staff/manager: 只看本部门
    """
    stmt = select(PatientProfile).where(PatientProfile.tenant_id == tenant_id)
    if effective_org_id is not None:
        stmt = stmt.where(PatientProfile.org_id == effective_org_id)
    if search:
        stmt = stmt.where(PatientProfile.real_name.ilike(f"%{search}%"))
    stmt = stmt.offset(skip).limit(limit).order_by(PatientProfile.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/me", response_model=PatientProfileRead)
async def get_my_patient_profile(
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
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
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("patient:read")),
    db: AsyncSession = Depends(get_db),
):
    """[管理视图] 获取特定患者详情
    - admin/owner: 可查看任意部门的患者
    - staff/manager: 只能查看本部门的患者
    """
    patient = await db.get(PatientProfile, patient_id)
    if not patient or patient.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    if effective_org_id is not None and patient.org_id != effective_org_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@router.put("/me", response_model=PatientProfileRead)
async def update_my_patient_profile(
    profile_in: PatientProfileUpdate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """[个人视图] 更新当前用户自己的患者档案"""
    profile = await _load_patient_profile(db, current_user.id, org_id)
    if not profile:
        profile = PatientProfile(user_id=current_user.id, tenant_id=tenant_id, org_id=org_id, real_name="Unnamed")
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
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("patient:update")),
    db: AsyncSession = Depends(get_db),
):
    """[管理视图] 管理员修改患者信息"""
    patient = await db.get(PatientProfile, patient_id)
    if not patient or patient.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    if effective_org_id is not None and patient.org_id != effective_org_id:
        raise HTTPException(status_code=404, detail="Patient not found")

    for field, value in profile_in.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.get("/me/suggestions")
async def get_my_suggestions(
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """[患者视图] 查看管理师给自己的管理建议"""
    from app.db.models import ManagementSuggestion

    profile = await _load_patient_profile(db, current_user.id, org_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    stmt = (
        select(ManagementSuggestion)
        .where(
            ManagementSuggestion.patient_id == profile.id,
            ManagementSuggestion.org_id == org_id,
        )
        .order_by(ManagementSuggestion.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# ── PatientProfile 管理员创建/删除 ──

from pydantic import BaseModel as _BaseModel

class PatientProfileAdminCreate(_BaseModel):
    user_id: int
    real_name: str
    gender: str | None = None
    birth_date: str | None = None
    medical_history: dict | None = None


@router.post("/create")
async def admin_create_patient_profile(
    data: PatientProfileAdminCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    _permission=Depends(check_permission("patient:create")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """[管理视图] 为用户创建患者档案（创建到当前部门）"""
    from app.db.models import User as UserModel

    stmt = select(UserModel).where(UserModel.id == data.user_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    existing = await _load_patient_profile(db, data.user_id, org_id)
    if existing:
        raise HTTPException(status_code=409, detail="Patient profile already exists")

    profile = PatientProfile(
        user_id=data.user_id,
        tenant_id=tenant_id,
        org_id=org_id,
        real_name=data.real_name,
        gender=data.gender,
        medical_history=data.medical_history,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return {
        "id": profile.id, "user_id": profile.user_id, "org_id": profile.org_id,
        "real_name": profile.real_name, "gender": profile.gender,
    }


@router.delete("/{patient_id}")
async def delete_patient_profile(
    patient_id: int,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("patient:delete")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """[管理视图] 删除患者档案"""
    patient = await db.get(PatientProfile, patient_id)
    if not patient or patient.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    if effective_org_id is not None and patient.org_id != effective_org_id:
        raise HTTPException(status_code=404, detail="Patient not found")

    await db.delete(patient)
    await db.commit()
    return {"status": "ok"}
