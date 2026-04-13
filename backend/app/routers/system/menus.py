"""菜单管理端点 — 纯 HTTP 适配层"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.models import OrganizationUser
from app.routers.deps import (
    MenuServiceDep,
    check_permission,
    get_current_org_id,
)

router = APIRouter()


# ── Schemas ──


class MenuCreate(BaseModel):
    parent_id: int | None = None
    name: str
    code: str
    menu_type: str = "page"
    path: str | None = None
    icon: str | None = None
    permission_code: str | None = None
    sort: int = 0
    is_visible: bool = True
    is_enabled: bool = True


class MenuUpdate(BaseModel):
    parent_id: int | None = None
    name: str | None = None
    menu_type: str | None = None
    path: str | None = None
    icon: str | None = None
    permission_code: str | None = None
    sort: int | None = None
    is_visible: bool | None = None
    is_enabled: bool | None = None


class MenuRead(BaseModel):
    id: int
    parent_id: int | None = None
    name: str
    code: str
    menu_type: str
    path: str | None = None
    icon: str | None = None
    permission_code: str | None = None
    sort: int = 0
    is_visible: bool = True
    is_enabled: bool = True
    children: list["MenuRead"] = []

    model_config = ConfigDict(from_attributes=True)


# ── 端点 ──


@router.get("", response_model=list[MenuRead])
async def list_menus(
    service: MenuServiceDep,
    _perm=Depends(check_permission("menu:manage")),
):
    """[管理员] 获取完整菜单树"""
    return await service.list_menu_tree()


@router.post("", response_model=MenuRead)
async def create_menu(
    data: MenuCreate,
    service: MenuServiceDep,
    org_id: int = Depends(get_current_org_id),
    _perm: OrganizationUser = Depends(check_permission("menu:manage")),
):
    """[管理员] 创建菜单"""
    return await service.create_menu(
        data.model_dump(), user_id=_perm.user_id, org_id=org_id
    )


@router.put("/{menu_id}", response_model=MenuRead)
async def update_menu(
    menu_id: int,
    data: MenuUpdate,
    service: MenuServiceDep,
    org_id: int = Depends(get_current_org_id),
    _perm: OrganizationUser = Depends(check_permission("menu:manage")),
):
    """[管理员] 更新菜单"""
    return await service.update_menu(
        menu_id, data.model_dump(exclude_unset=True), user_id=_perm.user_id, org_id=org_id
    )


@router.delete("/{menu_id}")
async def delete_menu(
    menu_id: int,
    service: MenuServiceDep,
    org_id: int = Depends(get_current_org_id),
    _perm: OrganizationUser = Depends(check_permission("menu:manage")),
):
    """[管理员] 删除菜单"""
    await service.delete_menu(menu_id, user_id=_perm.user_id, org_id=org_id)
    return {"status": "ok"}
