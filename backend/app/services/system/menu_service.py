"""菜单管理业务服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ConflictError, NotFoundError
from app.models import Menu
from app.repositories.menu_repo import MenuRepository


class MenuService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MenuRepository(db)

    async def list_menus(self) -> list[Menu]:
        """获取整个菜单树（扁平结构）"""
        return await self.repo.list_all()

    async def get_menu(self, menu_id: int) -> Menu:
        """获取单个菜单"""
        menu = await self.repo.get_by_id(menu_id)
        if not menu:
            raise NotFoundError("Menu", menu_id)
        return menu

    async def create_menu(self, data: dict) -> Menu:
        """创建菜单（全局）"""
        code = data.get("code")
        if code and await self.repo.check_code_exists(code):
            raise ConflictError("Menu code already exists")

        menu = Menu(**data)
        await self.repo.create(menu)
        await self.db.commit()
        return menu

    async def update_menu(self, menu_id: int, data: dict) -> Menu:
        """更新菜单信息"""
        menu = await self.repo.get_by_id(menu_id)
        if not menu:
            raise NotFoundError("Menu", menu_id)

        code = data.get("code")
        if code and code != menu.code and await self.repo.check_code_exists(code, exclude_id=menu_id):
            raise ConflictError("Menu code already exists")

        await self.repo.update(menu, data)
        await self.db.commit()
        return menu

    async def delete_menu(self, menu_id: int) -> None:
        """真删除菜单（需级联处理子菜单）"""
        menu = await self.repo.get_by_id(menu_id)
        if not menu:
            raise NotFoundError("Menu", menu_id)

        # 把所有子项一起删除（级联依赖）
        menus = await self.repo.list_all()
        to_delete = [menu]

        def collect_children(parent_id: int):
            for m in menus:
                if m.parent_id == parent_id:
                    to_delete.append(m)
                    collect_children(m.id)

        collect_children(menu.id)

        for m in reversed(to_delete):
            await self.repo.delete(m)

        await self.db.commit()
