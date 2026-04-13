from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, UsageLog
from app.repositories.base import BaseRepository


class UsageRepository(BaseRepository[UsageLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, UsageLog)

    async def get_summary_by_orgs(self):
        stmt = (
            select(
                self.model.org_id,
                Organization.name.label("org_name"),
                func.sum(self.model.prompt_tokens + self.model.completion_tokens).label("total_tokens"),
                func.coalesce(func.sum(self.model.cost), 0).label("total_cost"),
            )
            .join(Organization, Organization.id == self.model.org_id)
            .group_by(self.model.org_id, Organization.name)
            .order_by(func.sum(self.model.prompt_tokens + self.model.completion_tokens).desc())
        )
        result = await self.db.execute(stmt)
        return result.all()

    async def get_org_usage_detail(self, org_id: int):
        stmt = (
            select(
                self.model.user_id,
                func.sum(self.model.prompt_tokens + self.model.completion_tokens).label("total_tokens"),
                func.count(self.model.id).label("request_count"),
            )
            .where(self.model.org_id == org_id)
            .group_by(self.model.user_id)
            .order_by(func.sum(self.model.prompt_tokens + self.model.completion_tokens).desc())
        )
        result = await self.db.execute(stmt)
        return result.all()

    async def get_tenant_total_tokens(self, tenant_id: int) -> int:
        stmt = select(
            func.coalesce(func.sum(self.model.prompt_tokens + self.model.completion_tokens), 0)
        ).where(self.model.tenant_id == tenant_id)
        return (await self.db.execute(stmt)).scalar() or 0
