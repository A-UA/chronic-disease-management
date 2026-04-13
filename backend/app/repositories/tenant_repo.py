from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tenant
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Tenant)

    async def list_with_filters(
        self, search: str | None = None, status: str | None = None, skip: int = 0, limit: int = 50
    ) -> tuple[int, list[Tenant]]:
        base = select(self.model)
        if search:
            base = base.where(
                self.model.name.ilike(f"%{search}%") | self.model.slug.ilike(f"%{search}%")
            )
        if status:
            base = base.where(self.model.status == status)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = base.order_by(self.model.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())

    async def check_slug_exists(self, slug: str, exclude_id: int | None = None) -> bool:
        stmt = select(self.model).where(self.model.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def increment_token_usage(self, tenant_id: int, added_tokens: int) -> None:
        from sqlalchemy import update
        stmt = (
            update(self.model)
            .where(self.model.id == tenant_id)
            .values(quota_tokens_used=self.model.quota_tokens_used + added_tokens)
        )
        await self.db.execute(stmt)
