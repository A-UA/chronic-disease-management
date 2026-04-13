"""患者档案路由 — 纯 HTTP 适配层"""

from typing import Any

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.deps import (
    PatientServiceDep,
    check_permission,
    get_current_org_id,
    get_current_tenant_id,
    get_current_user,
    get_effective_org_id,
    inject_rls_context,
)
from app.schemas.patient import (
    PatientProfileAdminCreate,
    PatientProfileRead,
    PatientProfileUpdate,
)

router = APIRouter()


@router.get("", response_model=list[PatientProfileRead])
async def list_patients(
    service: PatientServiceDep,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("patient:read")),
):
    """[管理视图] 列出患者
    - admin/owner: 看全租户（RLS 保证隔离）
    - staff/manager: 只看本部门
    """
    return await service.list_patients(
        tenant_id=tenant_id,
        org_id=effective_org_id,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/me", response_model=PatientProfileRead)
async def get_my_patient_profile(
    service: PatientServiceDep,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org_id),
) -> Any:
    """[个人视图] 获取当前用户自己的患者档案"""
    return await service.get_my_profile(current_user.id, org_id)


@router.get("/me/suggestions")
async def get_my_suggestions(
    service: PatientServiceDep,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org_id),
):
    """[患者视图] 查看管理师给自己的管理建议"""
    return await service.get_my_suggestions(current_user.id, org_id)


@router.get("/{patient_id}", response_model=PatientProfileRead)
async def get_patient_detail(
    patient_id: int,
    service: PatientServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("patient:read")),
):
    """[管理视图] 获取特定患者详情"""
    return await service.get_patient(patient_id, tenant_id, effective_org_id)


@router.put("/me", response_model=PatientProfileRead)
async def update_my_patient_profile(
    profile_in: PatientProfileUpdate,
    service: PatientServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
) -> Any:
    """[个人视图] 更新当前用户自己的患者档案"""
    return await service.update_my_profile(
        current_user.id, tenant_id, org_id, profile_in.model_dump(exclude_unset=True)
    )


@router.put("/{patient_id}", response_model=PatientProfileRead)
async def admin_update_patient(
    patient_id: int,
    profile_in: PatientProfileUpdate,
    service: PatientServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("patient:update")),
):
    """[管理视图] 管理员修改患者信息"""
    return await service.admin_update_patient(
        patient_id,
        tenant_id,
        effective_org_id,
        profile_in.model_dump(exclude_unset=True),
    )


@router.post("/create")
async def admin_create_patient_profile(
    data: PatientProfileAdminCreate,
    service: PatientServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    _permission=Depends(check_permission("patient:create")),
) -> Any:
    """[管理视图] 为用户创建患者档案"""
    profile = await service.admin_create_patient(
        user_id=data.user_id,
        tenant_id=tenant_id,
        org_id=org_id,
        real_name=data.real_name,
        gender=data.gender,
        medical_history=data.medical_history,
    )
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "org_id": profile.org_id,
        "real_name": profile.real_name,
        "gender": profile.gender,
    }


@router.delete("/{patient_id}")
async def delete_patient_profile(
    patient_id: int,
    service: PatientServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("patient:delete")),
) -> Any:
    """[管理视图] 删除患者档案"""
    await service.delete_patient(patient_id, tenant_id, effective_org_id)
    return {"status": "ok"}
