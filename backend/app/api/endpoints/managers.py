from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_db, get_current_user, get_current_org, get_current_tenant_id, check_permission
from app.db.models import (
    User, 
    PatientProfile, 
    PatientManagerAssignment, 
    ManagementSuggestion,
    ManagerProfile
)

router = APIRouter()

# --- Schemas ---
class ManagerDetailRead(BaseModel):
    id: int
    user_id: int
    name: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    is_active: bool
    assigned_patient_count: int = 0
    model_config = ConfigDict(from_attributes=True)

class PatientBriefRead(BaseModel):
    id: int
    user_id: int
    real_name: str
    gender: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class SuggestionCreate(BaseModel):
    content: str
    suggestion_type: str = "general"

class SuggestionRead(BaseModel):
    id: int
    manager_id: int
    patient_id: int
    content: str
    suggestion_type: str
    created_at: Any
    model_config = ConfigDict(from_attributes=True)

class AssignmentCreate(BaseModel):
    patient_id: int
    manager_id: int
    assignment_role: str = "main"

# --- Unified Endpoints ---

@router.get("", response_model=List[ManagerDetailRead])
async def list_org_managers(
    org_id: int = Depends(get_current_org),
    _permission=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理视图] 列出本机构所有管理师及其工作负荷"""
    stmt = (
        select(ManagerProfile)
        .options(selectinload(ManagerProfile.user))
        .where(ManagerProfile.org_id == org_id)
    )
    result = await db.execute(stmt)
    managers = result.scalars().all()

    reads = []
    for m in managers:
        count_stmt = select(func.count(PatientManagerAssignment.patient_id)).where(
            PatientManagerAssignment.manager_id == m.user_id
        )
        count = (await db.execute(count_stmt)).scalar() or 0
        reads.append(ManagerDetailRead(
            id=m.id, user_id=m.user_id, title=m.title, is_active=m.is_active,
            name=m.user.name, email=m.user.email, assigned_patient_count=count
        ))
    return reads

@router.get("/my-patients", response_model=List[PatientBriefRead])
async def get_my_assigned_patients(
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """[管理师视图] 查看分配给我的患者"""
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

@router.post("/assignments")
async def create_assignment(
    data: AssignmentCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org),
    _permission=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理视图] 分配患者给管理师 (SSD 兼容)"""
    from sqlalchemy.dialects.postgresql import insert
    stmt = (
        insert(PatientManagerAssignment)
        .values(
            tenant_id=tenant_id, org_id=org_id, manager_id=data.manager_id, 
            patient_id=data.patient_id, assignment_role=data.assignment_role
        )
        .on_conflict_do_update(
            index_elements=["manager_id", "patient_id"],
            set_={"assignment_role": data.assignment_role}
        )
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "ok"}

@router.post("/patients/{patient_id}/suggestions", response_model=SuggestionRead)
async def create_patient_suggestion(
    patient_id: int,
    suggest_in: SuggestionCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org),
    _ = Depends(check_permission("suggestion:create")),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """[管理师视图] 为患者创建管理建议"""
    # 校验分配关系
    stmt = select(PatientManagerAssignment).where(
        PatientManagerAssignment.manager_id == current_user.id,
        PatientManagerAssignment.patient_id == patient_id,
        PatientManagerAssignment.org_id == org_id
    )
    if not (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not assigned to this patient")

    suggestion = ManagementSuggestion(
        tenant_id=tenant_id, org_id=org_id, manager_id=current_user.id,
        patient_id=patient_id, content=suggest_in.content,
        suggestion_type=suggest_in.suggestion_type
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)
    return suggestion

@router.get("/patients/{patient_id}/suggestions", response_model=List[SuggestionRead])
async def get_patient_suggestions(
    patient_id: int,
    org_id: int = Depends(get_current_org),
    _ = Depends(check_permission("suggestion:read")),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """获取患者的管理建议"""
    stmt = select(ManagementSuggestion).where(
        ManagementSuggestion.patient_id == patient_id,
        ManagementSuggestion.org_id == org_id
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/assignments/{patient_id}")
async def unassign_patient(
    patient_id: int,
    org_id: int = Depends(get_current_org),
    _ = Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """取消管理师与患者的分配关系"""
    from sqlalchemy import delete
    stmt = delete(PatientManagerAssignment).where(
        PatientManagerAssignment.patient_id == patient_id,
        PatientManagerAssignment.org_id == org_id,
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await db.commit()
    return {"status": "ok"}


# ── ManagerProfile CRUD ──

class ManagerProfileCreate(BaseModel):
    user_id: int
    title: str | None = None
    bio: str | None = None


class ManagerProfileUpdate(BaseModel):
    title: str | None = None
    bio: str | None = None
    is_active: bool | None = None


@router.post("/profiles")
async def create_manager_profile(
    data: ManagerProfileCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org),
    _permission=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """[管理视图] 创建管理师档案"""
    # 校验用户存在
    stmt = select(User).where(User.id == data.user_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    # 校验不重复
    stmt2 = select(ManagerProfile).where(
        ManagerProfile.user_id == data.user_id,
        ManagerProfile.org_id == org_id,
    )
    result2 = await db.execute(stmt2)
    if result2.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Manager profile already exists")

    profile = ManagerProfile(
        user_id=data.user_id,
        tenant_id=tenant_id,
        org_id=org_id,
        title=data.title,
        bio=data.bio,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return {
        "id": profile.id, "user_id": profile.user_id, "org_id": profile.org_id,
        "title": profile.title, "bio": profile.bio, "is_active": profile.is_active,
    }


@router.put("/profiles/{profile_id}")
async def update_manager_profile(
    profile_id: int,
    data: ManagerProfileUpdate,
    org_id: int = Depends(get_current_org),
    _permission=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """[管理视图] 更新管理师档案"""
    profile = await db.get(ManagerProfile, profile_id)
    if not profile or profile.org_id != org_id:
        raise HTTPException(status_code=404, detail="Manager profile not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return {
        "id": profile.id, "user_id": profile.user_id, "org_id": profile.org_id,
        "title": profile.title, "bio": profile.bio, "is_active": profile.is_active,
    }


@router.delete("/profiles/{profile_id}")
async def deactivate_manager_profile(
    profile_id: int,
    org_id: int = Depends(get_current_org),
    _permission=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """[管理视图] 停用管理师档案（软删除）"""
    profile = await db.get(ManagerProfile, profile_id)
    if not profile or profile.org_id != org_id:
        raise HTTPException(status_code=404, detail="Manager profile not found")

    profile.is_active = False
    await db.commit()
    return {"status": "ok"}


# ── ManagementSuggestion 更新/删除 ──

class SuggestionUpdate(BaseModel):
    content: str | None = None
    suggestion_type: str | None = None


@router.put("/suggestions/{suggestion_id}")
async def update_suggestion(
    suggestion_id: int,
    data: SuggestionUpdate,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    _ = Depends(check_permission("suggestion:create")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """[管理师视图] 修改自己发出的管理建议"""
    suggestion = await db.get(ManagementSuggestion, suggestion_id)
    if not suggestion or suggestion.org_id != org_id:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if suggestion.manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only edit your own suggestions")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(suggestion, field, value)
    await db.commit()
    await db.refresh(suggestion)
    return {
        "id": suggestion.id, "manager_id": suggestion.manager_id,
        "patient_id": suggestion.patient_id, "content": suggestion.content,
        "suggestion_type": suggestion.suggestion_type,
    }


@router.delete("/suggestions/{suggestion_id}")
async def delete_suggestion(
    suggestion_id: int,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    _ = Depends(check_permission("suggestion:create")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """[管理师视图] 撤回自己的管理建议"""
    suggestion = await db.get(ManagementSuggestion, suggestion_id)
    if not suggestion or suggestion.org_id != org_id:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if suggestion.manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own suggestions")

    await db.delete(suggestion)
    await db.commit()
    return {"status": "ok"}

