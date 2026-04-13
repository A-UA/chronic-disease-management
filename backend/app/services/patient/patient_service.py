"""患者档案业务服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ConflictError, NotFoundError
from app.models import PatientProfile, User
from app.repositories.patient_repo import PatientRepository


class PatientService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PatientRepository(db)

    async def list_patients(
        self,
        *,
        tenant_id: int,
        org_id: int | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PatientProfile]:
        """列出患者（管理视图）"""
        return await self.repo.search(
            tenant_id=tenant_id, org_id=org_id, name=search, skip=skip, limit=limit
        )

    async def get_my_profile(
        self, user_id: int, org_id: int
    ) -> PatientProfile:
        """获取当前用户自己的患者档案"""
        profile = await self.repo.find_by_user_and_org(user_id, org_id)
        if not profile:
            raise NotFoundError("Patient profile")
        return profile

    async def get_patient(
        self,
        patient_id: int,
        tenant_id: int,
        org_id: int | None = None,
    ) -> PatientProfile:
        """按 ID 获取患者，含 tenant/org 校验"""
        patient = await self.repo.get_by_id(patient_id)
        if not patient or patient.tenant_id != tenant_id:
            raise NotFoundError("Patient", patient_id)
        if org_id is not None and patient.org_id != org_id:
            raise NotFoundError("Patient", patient_id)
        return patient

    async def update_my_profile(
        self,
        user_id: int,
        tenant_id: int,
        org_id: int,
        data: dict,
    ) -> PatientProfile:
        """更新当前用户自己的档案（不存在则创建）"""
        profile = await self.repo.find_by_user_and_org(user_id, org_id)
        if not profile:
            profile = PatientProfile(
                user_id=user_id,
                tenant_id=tenant_id,
                org_id=org_id,
                real_name="Unnamed",
            )
            await self.repo.create(profile)
        if data:
            await self.repo.update(profile, data)
        await self.db.commit()
        return profile

    async def admin_update_patient(
        self,
        patient_id: int,
        tenant_id: int,
        org_id: int | None,
        data: dict,
    ) -> PatientProfile:
        """管理员修改患者信息"""
        patient = await self.get_patient(patient_id, tenant_id, org_id)
        await self.repo.update(patient, data)
        await self.db.commit()
        return patient

    async def admin_create_patient(
        self,
        *,
        user_id: int,
        tenant_id: int,
        org_id: int,
        real_name: str,
        gender: str | None = None,
        medical_history: dict | None = None,
    ) -> PatientProfile:
        """管理员为指定用户创建患者档案"""
        # 验证用户存在
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User", user_id)

        # 检查重复
        existing = await self.repo.find_by_user_and_org(user_id, org_id)
        if existing:
            raise ConflictError("Patient profile already exists")

        profile = PatientProfile(
            user_id=user_id,
            tenant_id=tenant_id,
            org_id=org_id,
            real_name=real_name,
            gender=gender,
            medical_history=medical_history,
        )
        await self.repo.create(profile)
        await self.db.commit()
        return profile

    async def delete_patient(
        self,
        patient_id: int,
        tenant_id: int,
        org_id: int | None = None,
    ) -> None:
        """删除患者档案"""
        patient = await self.get_patient(patient_id, tenant_id, org_id)
        await self.repo.delete(patient)
        await self.db.commit()

    async def get_my_suggestions(
        self, user_id: int, org_id: int
    ) -> list:
        """获取自己的管理建议"""
        profile = await self.get_my_profile(user_id, org_id)
        return await self.repo.get_suggestions_for_patient(profile.id, org_id)
