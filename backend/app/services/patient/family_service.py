"""家属关联业务服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ForbiddenError, NotFoundError
from app.models import PatientFamilyLink
from app.repositories.family_repo import FamilyRepository
from app.repositories.patient_repo import PatientRepository
from app.repositories.user_repo import UserRepository
from app.services.audit.service import audit_action


class FamilyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FamilyRepository(db)
        self.patient_repo = PatientRepository(db)
        self.user_repo = UserRepository(db)

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
        patient = await self.patient_repo.get_by_id(patient_id)
        if not patient or patient.org_id != org_id or patient.user_id != user_id:
            raise ForbiddenError("Not authorized to link this patient")

        family_user = await self.user_repo.get_by_email(family_user_email)
        if not family_user:
            raise NotFoundError("Family user")

        link = PatientFamilyLink(
            tenant_id=tenant_id,
            patient_id=patient_id,
            family_user_id=family_user.id,
            relationship_type=relationship_type,
            access_level=access_level,
            status="active",
        )
        await self.repo.create(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def get_my_linked_patients(
        self, user_id: int
    ) -> list[PatientFamilyLink]:
        """获取关联的患者列表"""
        return await self.repo.list_by_family_user(user_id)

    async def get_linked_patient_profile(
        self,
        patient_id: int,
        user_id: int,
    ) -> dict:
        """查看关联的患者档案"""
        link = await self.repo.get_active_link(patient_id, user_id)
        if not link:
            raise ForbiddenError("No active family link for this patient")

        patient = await self.patient_repo.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("Patient profile")

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
        link = await self.repo.get_link(patient_id, user_id)
        if not link:
            raise NotFoundError("Family link")

        await self.repo.delete(link)
        await self.db.commit()
