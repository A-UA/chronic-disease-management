"""用户管理端点 — 纯 HTTP 适配层"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.routers.deps import (
    UserServiceDep,
    check_permission,
    get_current_org_id,
    get_current_tenant_id,
)
from app.schemas.admin import UserAdminRead

router = APIRouter()


class UserCreateAdmin(BaseModel):
    email: str
    password: str
    name: str | None = None
    org_id: int | None = None
    role_ids: list[int] | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


@router.post("", response_model=UserAdminRead)
async def create_user(
    user_in: UserCreateAdmin,
    service: UserServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    current_org_id: int = Depends(get_current_org_id),
    _admin=Depends(check_permission("org_member:manage")),
):
    """[平台管理员] 创建用户并绑定到组织+角色"""
    return await service.create_user(
        email=user_in.email,
        password=user_in.password,
        name=user_in.name,
        tenant_id=tenant_id,
        org_id=user_in.org_id or current_org_id,
        role_ids=user_in.role_ids,
    )


@router.get("")
async def list_users(
    service: UserServiceDep,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    tenant_id: int = Depends(get_current_tenant_id),
    _admin=Depends(check_permission("org_member:manage")),
):
    """[管理员] 列出当前租户下的所有用户"""
    return await service.list_users(tenant_id, search=search, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserAdminRead)
async def get_user(
    user_id: int,
    service: UserServiceDep,
    _admin=Depends(check_permission("org_member:manage")),
):
    """[平台管理员] 获取用户详情"""
    return await service.get_user(user_id)


@router.put("/{user_id}", response_model=UserAdminRead)
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: UserServiceDep,
    _admin=Depends(check_permission("org_member:manage")),
):
    """[平台管理员] 编辑用户信息"""
    return await service.update_user(user_id, data.model_dump(exclude_unset=True))


@router.put("/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    service: UserServiceDep,
    _admin=Depends(check_permission("org_member:manage")),
):
    """[平台管理员] 启用/禁用用户"""
    await service.update_user_status(user_id, is_active)
    return {"status": "ok"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    service: UserServiceDep,
    _admin=Depends(check_permission("org_member:manage")),
):
    """[平台管理员] 删除用户（软删除）"""
    await service.delete_user(user_id)
    return {"status": "ok"}
