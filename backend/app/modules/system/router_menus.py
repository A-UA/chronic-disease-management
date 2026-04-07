"""菜单管理 CRUD 端点"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import check_permission, get_current_org_id, get_db
from app.db.models import Menu, OrganizationUser
from app.modules.audit.service import fire_audit

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
    _perm=Depends(check_permission("menu:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 获取完整菜单树（管理视图，含不可见菜单）"""
    stmt = (
        select(Menu)
        .where(Menu.parent_id.is_(None))
        .options(selectinload(Menu.children).selectinload(Menu.children))
        .order_by(Menu.sort)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=MenuRead)
async def create_menu(
    data: MenuCreate,
    org_id: int = Depends(get_current_org_id),
    _perm: OrganizationUser = Depends(check_permission("menu:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 创建菜单"""
    # code 唯一性检查
    stmt = select(Menu).where(Menu.code == data.code)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Menu code already exists")

    # 如指定了 parent_id，验证父菜单存在
    if data.parent_id:
        parent = await db.get(Menu, data.parent_id)
        if not parent:
            raise HTTPException(status_code=400, detail="Parent menu not found")

    menu = Menu(**data.model_dump())
    db.add(menu)
    await db.flush()

    fire_audit(
        user_id=_perm.user_id, org_id=org_id,
        action="CREATE_MENU", resource_type="menu",
        resource_id=menu.id, details=f"Created menu: {menu.name} ({menu.code})",
    )

    await db.commit()
    await db.refresh(menu)
    return menu


@router.put("/{menu_id}", response_model=MenuRead)
async def update_menu(
    menu_id: int,
    data: MenuUpdate,
    org_id: int = Depends(get_current_org_id),
    _perm: OrganizationUser = Depends(check_permission("menu:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 更新菜单"""
    menu = await db.get(Menu, menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    # 防止自引用
    if data.parent_id and data.parent_id == menu_id:
        raise HTTPException(status_code=400, detail="Menu cannot be its own parent")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(menu, field, value)

    fire_audit(
        user_id=_perm.user_id, org_id=org_id,
        action="UPDATE_MENU", resource_type="menu",
        resource_id=menu.id, details=f"Updated menu: {menu.name}",
    )

    await db.commit()
    await db.refresh(menu)
    return menu


@router.delete("/{menu_id}")
async def delete_menu(
    menu_id: int,
    org_id: int = Depends(get_current_org_id),
    _perm: OrganizationUser = Depends(check_permission("menu:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 删除菜单（含子菜单级联删除）"""
    menu = await db.get(Menu, menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    fire_audit(
        user_id=_perm.user_id, org_id=org_id,
        action="DELETE_MENU", resource_type="menu",
        resource_id=menu.id, details=f"Deleted menu: {menu.name} ({menu.code})",
    )

    await db.delete(menu)
    await db.commit()
    return {"status": "ok"}
