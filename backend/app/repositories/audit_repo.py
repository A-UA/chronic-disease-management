from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, AuditLog)

    async def list_audit_logs(
        self,
        tenant_id: int | None = None,
        org_id: int | None = None,
        user_id: int | None = None,
        action: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, list[AuditLog]]:
        base = select(self.model)

        if tenant_id is not None:
            base = base.where(self.model.tenant_id == tenant_id)
        if org_id is not None:
            base = base.where(self.model.org_id == org_id)
        if user_id is not None:
            base = base.where(self.model.user_id == user_id)
        if action is not None:
            base = base.where(self.model.action == action)
        if start_time is not None:
            base = base.where(self.model.created_at >= start_time)
        if end_time is not None:
            base = base.where(self.model.created_at <= end_time)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = base.order_by(self.model.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())
