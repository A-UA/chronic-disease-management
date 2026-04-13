"""RBAC 管理端点 — 纯 HTTP 适配层"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models import OrganizationUser
from app.routers.deps import (
    RBACServiceDep,
    check_org_admin,
    get_current_org_id,
    get_current_tenant_id,
)
from app.schemas.rbac import RoleCreate, RoleRead

router = APIRouter()


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permission_ids: list[int] | None = None


@router.get("/resources", response_model=list[dict])
async def list_resources(
    service: RBACServiceDep,
    _org_admin=Depends(check_org_admin()),
):
    """[管理员] 获取系统受保护资源字典"""
    return await service.list_resources()


@router.get("/actions", response_model=list[dict])
async def list_actions(
    service: RBACServiceDep,
    _org_admin=Depends(check_org_admin()),
):
    """[管理员] 获取系统操作行为字典"""
    return await service.list_actions()


@router.get("/permissions", response_model=list[dict])
async def list_permissions(
    service: RBACServiceDep,
    _org_admin=Depends(check_org_admin()),
):
    """[管理员] 获取系统所有权限列表"""
    return await service.list_permissions()


@router.get("/roles")
async def list_roles(
    service: RBACServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    _org_admin=Depends(check_org_admin()),
):
    """获取本组织可用角色列表"""
    return await service.list_roles(tenant_id, org_id)


@router.post("/roles", response_model=RoleRead)
async def create_custom_role(
    role_in: RoleCreate,
    service: RBACServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    org_admin: OrganizationUser = Depends(check_org_admin()),
):
    """[管理员] 创建组织自定义角色"""
    return await service.create_role(
        tenant_id=tenant_id,
        org_id=org_id,
        admin_user_id=org_admin.user_id,
        name=role_in.name,
        code=role_in.code,
        description=role_in.description,
        parent_role_id=role_in.parent_role_id,
        permission_ids=role_in.permission_ids,
    )


@router.post("/members/{user_id}/roles")
async def assign_user_roles(
    user_id: int,
    role_ids: list[int],
    service: RBACServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    org_admin: OrganizationUser = Depends(check_org_admin()),
):
    """[管理员] 为组织成员授权"""
    return await service.assign_user_roles(
        tenant_id=tenant_id,
        org_id=org_id,
        admin_user_id=org_admin.user_id,
        user_id=user_id,
        role_ids=role_ids,
    )


@router.put("/roles/{role_id}")
async def update_role(
    role_id: int,
    data: RoleUpdate,
    service: RBACServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    _org_admin=Depends(check_org_admin()),
):
    """[管理员] 更新自定义角色"""
    return await service.update_role(role_id, tenant_id, data.model_dump(exclude_unset=True))


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    service: RBACServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    _org_admin=Depends(check_org_admin()),
):
    """[管理员] 删除自定义角色"""
    await service.delete_role(role_id, tenant_id)
    return {"status": "ok"}
