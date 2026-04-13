"""通用数据访问基类，提供标准 CRUD 操作

Repository 只使用 flush() 而非 commit()，事务控制权在 Service 层。
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """泛型 Repository 基类"""

    def __init__(self, db: AsyncSession, model: type[ModelType]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: int) -> ModelType | None:
        """按主键获取"""
        return await self.db.get(self.model, id)

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        filters: list[Any] | None = None,
        order_by: Any = None,
    ) -> list[ModelType]:
        """通用列表查询"""
        stmt = select(self.model)
        for f in filters or []:
            stmt = stmt.where(f)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *, filters: list[Any] | None = None) -> int:
        """通用计数"""
        stmt = select(func.count()).select_from(self.model)
        for f in filters or []:
            stmt = stmt.where(f)
        return (await self.db.execute(stmt)).scalar() or 0

    async def create(self, obj: ModelType) -> ModelType:
        """插入对象（flush，不 commit）"""
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelType, data: dict[str, Any]) -> ModelType:
        """部分更新（flush，不 commit）"""
        for key, value in data.items():
            setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        """删除对象（flush，不 commit）"""
        await self.db.delete(obj)
        await self.db.flush()
