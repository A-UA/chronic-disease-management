"""管理师数据访问"""

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ManagementSuggestion,
    ManagerProfile,
    PatientManagerAssignment,
    PatientProfile,
    User,
)
from app.repositories.base import BaseRepository


class ManagerRepository(BaseRepository[ManagerProfile]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ManagerProfile)

    async def list_with_user(
        self,
        tenant_id: int,
        org_id: int | None = None,
    ) -> list[ManagerProfile]:
        """列出管理师（含 user 关联）"""
        stmt = (
            select(ManagerProfile)
            .options(selectinload(ManagerProfile.user))
            .where(ManagerProfile.tenant_id == tenant_id)
        )
        if org_id is not None:
            stmt = stmt.where(ManagerProfile.org_id == org_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_assignments(self, manager_user_id: int) -> int:
        """统计管理师负责的患者数"""
        stmt = select(func.count(PatientManagerAssignment.patient_id)).where(
            PatientManagerAssignment.manager_id == manager_user_id
        )
        return (await self.db.execute(stmt)).scalar() or 0

    async def find_by_user_and_org(
        self, user_id: int, org_id: int
    ) -> ManagerProfile | None:
        """按用户 + 组织查找管理师"""
        stmt = select(ManagerProfile).where(
            ManagerProfile.user_id == user_id,
            ManagerProfile.org_id == org_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_assigned_patients(
        self, manager_user_id: int, org_id: int
    ) -> list[PatientProfile]:
        """获取管理师分配的患者列表"""
        stmt = (
            select(PatientProfile)
            .join(
                PatientManagerAssignment,
                PatientProfile.id == PatientManagerAssignment.patient_id,
            )
            .where(
                PatientManagerAssignment.manager_id == manager_user_id,
                PatientManagerAssignment.org_id == org_id,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def upsert_assignment(
        self,
        *,
        tenant_id: int,
        org_id: int,
        manager_id: int,
        patient_id: int,
        assignment_role: str,
    ) -> None:
        """创建或更新分配关系（ON CONFLICT）"""
        stmt = (
            insert(PatientManagerAssignment)
            .values(
                tenant_id=tenant_id,
                org_id=org_id,
                manager_id=manager_id,
                patient_id=patient_id,
                assignment_role=assignment_role,
            )
            .on_conflict_do_update(
                index_elements=["manager_id", "patient_id"],
                set_={"assignment_role": assignment_role},
            )
        )
        await self.db.execute(stmt)

    async def delete_assignments(
        self,
        patient_id: int,
        tenant_id: int,
        org_id: int | None = None,
    ) -> int:
        """删除分配关系，返回受影响行数"""
        stmt = delete(PatientManagerAssignment).where(
            PatientManagerAssignment.patient_id == patient_id,
            PatientManagerAssignment.tenant_id == tenant_id,
        )
        if org_id is not None:
            stmt = stmt.where(PatientManagerAssignment.org_id == org_id)
        result = await self.db.execute(stmt)
        return result.rowcount

    async def find_assignment(
        self, manager_id: int, patient_id: int, org_id: int
    ) -> PatientManagerAssignment | None:
        """查找分配关系"""
        stmt = select(PatientManagerAssignment).where(
            PatientManagerAssignment.manager_id == manager_id,
            PatientManagerAssignment.patient_id == patient_id,
            PatientManagerAssignment.org_id == org_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_suggestions(
        self,
        patient_id: int,
        tenant_id: int,
        org_id: int | None = None,
    ) -> list[ManagementSuggestion]:
        """获取患者的管理建议"""
        stmt = select(ManagementSuggestion).where(
            ManagementSuggestion.patient_id == patient_id,
            ManagementSuggestion.tenant_id == tenant_id,
        )
        if org_id is not None:
            stmt = stmt.where(ManagementSuggestion.org_id == org_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_user(self, user_id: int) -> User | None:
        """查找用户"""
        return await self.db.get(User, user_id)
