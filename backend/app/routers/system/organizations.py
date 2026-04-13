"""组织管理端点 — 纯 HTTP 适配层"""

from typing import Any

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.deps import (
    OrgServiceDep,
    check_permission,
    get_current_tenant_id,
    get_current_user,
)
from app.schemas.organization import (
    AddMemberRequest,
    OrganizationCreate,
    OrganizationInvitationCreate,
    OrganizationInvitationRead,
    OrganizationMemberRead,
    OrganizationReadAdmin,
    OrganizationReadPublic,
    OrganizationUpdate,
)

router = APIRouter()


@router.get("/me", response_model=list[OrganizationReadAdmin])
async def get_my_organizations(
    service: OrgServiceDep,
    current_user: User = Depends(get_current_user),
) -> Any:
    """[通用] 获取当前用户所属的所有机构"""
    return await service.get_my_organizations(current_user.id)


@router.get("")
async def list_organizations(
    service: OrgServiceDep,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    tenant_id: int = Depends(get_current_tenant_id),
    _permission=Depends(check_permission("org_member:manage")),
):
    """[管理视图] 列出当前租户的所有组织"""
    return await service.list_organizations(
        tenant_id, search=search, skip=skip, limit=limit
    )


@router.post("", response_model=OrganizationReadPublic)
async def create_organization(
    org_in: OrganizationCreate,
    service: OrgServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    _permission=Depends(check_permission("org_member:manage")),
):
    """[管理视图] 创建新机构"""
    effective_tenant_id = org_in.tenant_id or tenant_id
    return await service.create_organization(
        tenant_id=effective_tenant_id,
        name=org_in.name,
        code=org_in.code,
        status=org_in.status,
        description=org_in.description,
        parent_id=org_in.parent_id,
    )


@router.put("/{org_id}", response_model=OrganizationReadPublic)
async def update_organization(
    org_id: int,
    org_in: OrganizationUpdate,
    service: OrgServiceDep,
    _permission=Depends(check_permission("org_member:manage")),
) -> Any:
    """[管理视图] 编辑机构信息"""
    return await service.update_organization(
        org_id, org_in.model_dump(exclude_unset=True)
    )


@router.delete("/{org_id}")
async def delete_organization(
    org_id: int,
    service: OrgServiceDep,
    _permission=Depends(check_permission("org_member:manage")),
):
    """[管理视图] 删除组织"""
    await service.delete_organization(org_id)
    return {"status": "ok"}


@router.get("/{org_id}/members", response_model=list[OrganizationMemberRead])
async def get_organization_members(
    org_id: int,
    service: OrgServiceDep,
    _permission=Depends(check_permission("org_member:manage")),
) -> Any:
    """[管理视图] 获取机构成员列表 (含角色)"""
    return await service.get_members(org_id)


@router.post("/{org_id}/members", response_model=dict)
async def add_organization_member(
    org_id: int,
    data: AddMemberRequest,
    service: OrgServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    _permission=Depends(check_permission("org_member:manage")),
):
    """[管理视图] 添加成员到组织"""
    await service.add_member(
        org_id=org_id,
        tenant_id=tenant_id,
        user_id=data.user_id,
        role_ids=data.role_ids,
        user_type=data.user_type,
    )
    return {"status": "ok"}


@router.delete("/{org_id}/members/{user_id}", response_model=dict)
async def remove_organization_member(
    org_id: int,
    user_id: int,
    service: OrgServiceDep,
    _permission=Depends(check_permission("org_member:manage")),
):
    """[管理视图] 移除机构成员"""
    await service.remove_member(org_id, user_id)
    return {"message": "Member removed successfully"}


@router.get("/{org_id}/invitations", response_model=list[OrganizationInvitationRead])
async def list_invitations(
    org_id: int,
    service: OrgServiceDep,
    _permission=Depends(check_permission("org_member:manage")),
):
    """[管理视图] 列出机构的待处理邀请"""
    return await service.list_invitations(org_id)


@router.post("/{org_id}/invitations", response_model=OrganizationInvitationRead)
async def create_invitation(
    org_id: int,
    invitation_in: OrganizationInvitationCreate,
    service: OrgServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    _permission=Depends(check_permission("org_member:manage")),
):
    """[管理视图] 发起组织邀请"""
    return await service.create_invitation(
        org_id=org_id,
        tenant_id=tenant_id,
        inviter_id=current_user.id,
        email=invitation_in.email,
        role=invitation_in.role,
    )


@router.post("/invitations/{token}/accept", response_model=dict)
async def accept_invitation(
    token: str,
    service: OrgServiceDep,
    current_user: User = Depends(get_current_user),
):
    """[通用] 接受组织邀请"""
    return await service.accept_invitation(token, current_user)
