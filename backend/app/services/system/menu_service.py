"""菜单管理业务服务"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.base.exceptions import ConflictError, NotFoundError, ValidationError
from app.models import Menu
from app.services.audit.service import fire_audit


class MenuService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_menu_tree(self) -> list[Menu]:
        """获取完整菜单树"""
        stmt = (
            select(Menu)
            .where(Menu.parent_id.is_(None))
            .options(selectinload(Menu.children).selectinload(Menu.children))
            .order_by(Menu.sort)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_menu(
        self, data: dict, *, user_id: int, org_id: int
    ) -> Menu:
        """创建菜单"""
        code = data.get("code")
        stmt = select(Menu).where(Menu.code == code)
        if (await self.db.execute(stmt)).scalar_one_or_none():
            raise ConflictError("Menu code already exists")

        parent_id = data.get("parent_id")
        if parent_id:
            parent = await self.db.get(Menu, parent_id)
            if not parent:
                raise NotFoundError("Parent menu", parent_id)

        menu = Menu(**data)
        self.db.add(menu)
        await self.db.flush()

        fire_audit(
            user_id=user_id,
            org_id=org_id,
            action="CREATE_MENU",
            resource_type="menu",
            resource_id=menu.id,
            details=f"Created menu: {menu.name} ({menu.code})",
        )

        await self.db.commit()
        await self.db.refresh(menu)
        return menu

    async def update_menu(
        self, menu_id: int, data: dict, *, user_id: int, org_id: int
    ) -> Menu:
        """更新菜单"""
        menu = await self.db.get(Menu, menu_id)
        if not menu:
            raise NotFoundError("Menu", menu_id)

        if data.get("parent_id") and data["parent_id"] == menu_id:
            raise ValidationError("Menu cannot be its own parent")

        for field, value in data.items():
            setattr(menu, field, value)

        fire_audit(
            user_id=user_id,
            org_id=org_id,
            action="UPDATE_MENU",
            resource_type="menu",
            resource_id=menu.id,
            details=f"Updated menu: {menu.name}",
        )

        await self.db.commit()
        await self.db.refresh(menu)
        return menu

    async def delete_menu(
        self, menu_id: int, *, user_id: int, org_id: int
    ) -> None:
        """删除菜单"""
        menu = await self.db.get(Menu, menu_id)
        if not menu:
            raise NotFoundError("Menu", menu_id)

        fire_audit(
            user_id=user_id,
            org_id=org_id,
            action="DELETE_MENU",
            resource_type="menu",
            resource_id=menu.id,
            details=f"Deleted menu: {menu.name} ({menu.code})",
        )

        await self.db.delete(menu)
        await self.db.commit()
