"""管理师管理端点 — 纯 HTTP 适配层"""

from typing import Any

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.deps import (
    ManagerServiceDep,
    check_permission,
    get_current_org_id,
    get_current_tenant_id,
    get_current_user,
    get_effective_org_id,
    inject_rls_context,
)
from app.schemas.manager import (
    AssignmentCreate,
    ManagerDetailRead,
    ManagerProfileCreate,
    ManagerProfileUpdate,
    PatientBriefRead,
    SuggestionCreate,
    SuggestionRead,
    SuggestionUpdate,
)

router = APIRouter()


# --- 查询类端点（admin 跨部门） ---


@router.get("", response_model=list[ManagerDetailRead])
async def list_org_managers(
    service: ManagerServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("org_member:manage")),
):
    """[管理视图] 列出管理师及其工作负荷"""
    return await service.list_org_managers(tenant_id, effective_org_id)


# --- 个人视图端点 ---


@router.get("/my-patients", response_model=list[PatientBriefRead])
async def get_my_assigned_patients(
    service: ManagerServiceDep,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org_id),
) -> Any:
    """[管理师视图] 查看分配给我的患者"""
    return await service.get_my_assigned_patients(current_user.id, org_id)


# --- 创建类端点 ---


@router.post("/assignments")
async def create_assignment(
    data: AssignmentCreate,
    service: ManagerServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    _permission=Depends(check_permission("org_member:manage")),
):
    """[管理视图] 分配患者给管理师"""
    await service.create_assignment(
        tenant_id=tenant_id,
        org_id=org_id,
        manager_id=data.manager_id,
        patient_id=data.patient_id,
        assignment_role=data.assignment_role,
    )
    return {"status": "ok"}


@router.post("/patients/{patient_id}/suggestions", response_model=SuggestionRead)
async def create_patient_suggestion(
    patient_id: int,
    suggest_in: SuggestionCreate,
    service: ManagerServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    _=Depends(check_permission("suggestion:create")),
) -> Any:
    """[管理师视图] 为患者创建管理建议"""
    return await service.create_suggestion(
        user_id=current_user.id,
        tenant_id=tenant_id,
        org_id=org_id,
        patient_id=patient_id,
        content=suggest_in.content,
        suggestion_type=suggest_in.suggestion_type,
    )


@router.get("/patients/{patient_id}/suggestions", response_model=list[SuggestionRead])
async def get_patient_suggestions(
    patient_id: int,
    service: ManagerServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _=Depends(check_permission("suggestion:read")),
) -> Any:
    """获取患者的管理建议"""
    return await service.get_patient_suggestions(
        patient_id, tenant_id, effective_org_id
    )


@router.delete("/assignments/{patient_id}")
async def unassign_patient(
    patient_id: int,
    service: ManagerServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _=Depends(check_permission("org_member:manage")),
) -> Any:
    """取消管理师与患者的分配关系"""
    await service.unassign_patient(patient_id, tenant_id, effective_org_id)
    return {"status": "ok"}


# ── ManagerProfile CRUD ──


@router.post("/profiles")
async def create_manager_profile(
    data: ManagerProfileCreate,
    service: ManagerServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    _permission=Depends(check_permission("org_member:manage")),
) -> Any:
    """[管理视图] 创建管理师档案"""
    return await service.create_manager_profile(
        user_id=data.user_id,
        tenant_id=tenant_id,
        org_id=org_id,
        title=data.title,
        bio=data.bio,
    )


@router.put("/profiles/{profile_id}")
async def update_manager_profile(
    profile_id: int,
    data: ManagerProfileUpdate,
    service: ManagerServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("org_member:manage")),
) -> Any:
    """[管理视图] 更新管理师档案"""
    return await service.update_manager_profile(
        profile_id, tenant_id, effective_org_id, data.model_dump(exclude_unset=True)
    )


@router.delete("/profiles/{profile_id}")
async def deactivate_manager_profile(
    profile_id: int,
    service: ManagerServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("org_member:manage")),
) -> Any:
    """[管理视图] 停用管理师档案（软删除）"""
    await service.deactivate_manager_profile(profile_id, tenant_id, effective_org_id)
    return {"status": "ok"}


# ── ManagementSuggestion 更新/删除 ──


@router.put("/suggestions/{suggestion_id}")
async def update_suggestion(
    suggestion_id: int,
    data: SuggestionUpdate,
    service: ManagerServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
    _=Depends(check_permission("suggestion:create")),
) -> Any:
    """[管理师视图] 修改自己发出的管理建议"""
    return await service.update_suggestion(
        suggestion_id, current_user.id, tenant_id, data.model_dump(exclude_unset=True)
    )


@router.delete("/suggestions/{suggestion_id}")
async def delete_suggestion(
    suggestion_id: int,
    service: ManagerServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
    _=Depends(check_permission("suggestion:create")),
) -> Any:
    """[管理师视图] 撤回自己的管理建议"""
    await service.delete_suggestion(suggestion_id, current_user.id, tenant_id)
    return {"status": "ok"}
