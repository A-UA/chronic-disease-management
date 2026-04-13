from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Menu
from app.repositories.base import BaseRepository


class MenuRepository(BaseRepository[Menu]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Menu)

    async def list_all(self) -> list[Menu]:
        stmt = select(self.model).order_by(self.model.sort, self.model.id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def check_code_exists(self, code: str, exclude_id: int | None = None) -> bool:
        stmt = select(self.model).where(self.model.code == code)
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def list_active(self, tenant_id: int) -> list[Menu]:
        stmt = (
            select(self.model)
            .where(
                self.model.is_enabled == True,
                self.model.deleted_at.is_(None),
                (self.model.tenant_id.is_(None)) | (self.model.tenant_id == tenant_id),
            )
            .order_by(self.model.sort)
        )
        return list((await self.db.execute(stmt)).scalars().all())
