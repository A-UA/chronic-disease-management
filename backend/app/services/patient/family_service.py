"""家属关联业务服务"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ForbiddenError, NotFoundError
from app.models import PatientFamilyLink, PatientProfile, User
from app.services.audit.service import audit_action


class FamilyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_link(
        self,
        *,
        user_id: int,
        tenant_id: int,
        org_id: int,
        patient_id: int,
        family_user_email: str,
        relationship_type: str | None = None,
        access_level: int = 1,
    ) -> PatientFamilyLink:
        """创建家属关联"""
        # 1. 验证患者属于当前用户
        stmt = select(PatientProfile).where(
            PatientProfile.id == patient_id,
            PatientProfile.org_id == org_id,
            PatientProfile.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        if not result.scalar_one_or_none():
            raise ForbiddenError("Not authorized to link this patient")

        # 2. 查找家属用户
        stmt_user = select(User).where(User.email == family_user_email)
        res_user = await self.db.execute(stmt_user)
        family_user = res_user.scalar_one_or_none()
        if not family_user:
            raise NotFoundError("Family user")

        # 3. 创建关联
        link = PatientFamilyLink(
            tenant_id=tenant_id,
            patient_id=patient_id,
            family_user_id=family_user.id,
            relationship_type=relationship_type,
            access_level=access_level,
            status="active",
        )
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def get_my_linked_patients(
        self, user_id: int
    ) -> list[PatientFamilyLink]:
        """获取关联的患者列表"""
        stmt = select(PatientFamilyLink).where(
            PatientFamilyLink.family_user_id == user_id,
            PatientFamilyLink.status == "active",
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_linked_patient_profile(
        self,
        patient_id: int,
        user_id: int,
    ) -> dict:
        """查看关联的患者档案"""
        # 1. 验证关联
        stmt = select(PatientFamilyLink).where(
            PatientFamilyLink.patient_id == patient_id,
            PatientFamilyLink.family_user_id == user_id,
            PatientFamilyLink.status == "active",
        )
        result = await self.db.execute(stmt)
        link = result.scalar_one_or_none()
        if not link:
            raise ForbiddenError("No active family link for this patient")

        # 2. 获取患者档案
        stmt_p = select(PatientProfile).where(PatientProfile.id == patient_id)
        res_p = await self.db.execute(stmt_p)
        patient = res_p.scalar_one_or_none()
        if not patient:
            raise NotFoundError("Patient profile")

        # 3. 审计日志
        await audit_action(
            self.db,
            user_id=user_id,
            org_id=patient.org_id,
            action="view_patient_family",
            resource_type="PatientProfile",
            resource_id=patient.id,
        )
        await self.db.commit()

        return {
            "id": patient.id,
            "real_name": patient.real_name,
            "gender": patient.gender,
            "birth_date": patient.birth_date,
            "medical_history": patient.medical_history,
            "relationship_type": link.relationship_type,
        }

    async def unlink(self, patient_id: int, user_id: int) -> None:
        """解除家属关联"""
        stmt = select(PatientFamilyLink).where(
            PatientFamilyLink.patient_id == patient_id,
            PatientFamilyLink.family_user_id == user_id,
        )
        result = await self.db.execute(stmt)
        link = result.scalar_one_or_none()
        if not link:
            raise NotFoundError("Family link")

        await self.db.delete(link)
        await self.db.commit()
