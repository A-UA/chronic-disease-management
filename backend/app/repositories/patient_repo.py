"""患者档案数据访问"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ManagementSuggestion, PatientProfile
from app.repositories.base import BaseRepository


class PatientRepository(BaseRepository[PatientProfile]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, PatientProfile)

    async def find_by_user_and_org(
        self, user_id: int, org_id: int
    ) -> PatientProfile | None:
        """按用户 ID + 组织 ID 查找患者档案"""
        stmt = select(PatientProfile).where(
            PatientProfile.user_id == user_id,
            PatientProfile.org_id == org_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        tenant_id: int,
        org_id: int | None = None,
        name: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PatientProfile]:
        """带搜索、分页、部门过滤的患者查询"""
        filters = [PatientProfile.tenant_id == tenant_id]
        if org_id is not None:
            filters.append(PatientProfile.org_id == org_id)
        if name:
            filters.append(PatientProfile.real_name.ilike(f"%{name}%"))
        return await self.list(
            filters=filters,
            skip=skip,
            limit=limit,
            order_by=PatientProfile.created_at.desc(),
        )

    async def get_suggestions_for_patient(
        self, patient_id: int, org_id: int
    ) -> list[ManagementSuggestion]:
        """获取患者的管理建议"""
        stmt = (
            select(ManagementSuggestion)
            .where(
                ManagementSuggestion.patient_id == patient_id,
                ManagementSuggestion.org_id == org_id,
            )
            .order_by(ManagementSuggestion.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
