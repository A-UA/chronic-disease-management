"""管理师业务服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models import ManagementSuggestion, ManagerProfile
from app.repositories.manager_repo import ManagerRepository
from app.schemas.manager import ManagerDetailRead


class ManagerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ManagerRepository(db)

    async def list_org_managers(
        self, tenant_id: int, org_id: int | None
    ) -> list[ManagerDetailRead]:
        """列出管理师及其工作负荷"""
        managers = await self.repo.list_with_user(tenant_id, org_id)
        reads = []
        for m in managers:
            count = await self.repo.count_assignments(m.user_id)
            reads.append(
                ManagerDetailRead(
                    id=m.id,
                    user_id=m.user_id,
                    title=m.title,
                    is_active=m.is_active,
                    name=m.user.name,
                    email=m.user.email,
                    assigned_patient_count=count,
                )
            )
        return reads

    async def get_my_assigned_patients(self, user_id: int, org_id: int) -> list:
        """管理师查看分配给自己的患者"""
        return await self.repo.get_assigned_patients(user_id, org_id)

    async def create_assignment(
        self,
        *,
        tenant_id: int,
        org_id: int,
        manager_id: int,
        patient_id: int,
        assignment_role: str,
    ) -> None:
        """分配患者给管理师"""
        await self.repo.upsert_assignment(
            tenant_id=tenant_id,
            org_id=org_id,
            manager_id=manager_id,
            patient_id=patient_id,
            assignment_role=assignment_role,
        )
        await self.db.commit()

    async def unassign_patient(
        self,
        patient_id: int,
        tenant_id: int,
        org_id: int | None,
    ) -> None:
        """取消分配关系"""
        count = await self.repo.delete_assignments(patient_id, tenant_id, org_id)
        if count == 0:
            raise NotFoundError("Assignment")
        await self.db.commit()

    async def create_suggestion(
        self,
        *,
        user_id: int,
        tenant_id: int,
        org_id: int,
        patient_id: int,
        content: str,
        suggestion_type: str,
    ) -> ManagementSuggestion:
        """为患者创建管理建议"""
        assignment = await self.repo.find_assignment(user_id, patient_id, org_id)
        if not assignment:
            raise ForbiddenError("Not assigned to this patient")

        suggestion = ManagementSuggestion(
            tenant_id=tenant_id,
            org_id=org_id,
            manager_id=user_id,
            patient_id=patient_id,
            content=content,
            suggestion_type=suggestion_type,
        )
        self.db.add(suggestion)
        await self.db.flush()
        await self.db.refresh(suggestion)
        await self.db.commit()
        return suggestion

    async def get_patient_suggestions(
        self,
        patient_id: int,
        tenant_id: int,
        org_id: int | None,
    ) -> list[ManagementSuggestion]:
        """获取患者的管理建议"""
        return await self.repo.list_suggestions(patient_id, tenant_id, org_id)

    async def update_suggestion(
        self,
        suggestion_id: int,
        user_id: int,
        tenant_id: int,
        data: dict,
    ) -> dict:
        """修改自己发出的管理建议"""
        suggestion = await self.db.get(ManagementSuggestion, suggestion_id)
        if not suggestion or suggestion.tenant_id != tenant_id:
            raise NotFoundError("Suggestion", suggestion_id)
        if suggestion.manager_id != user_id:
            raise ForbiddenError("Can only edit your own suggestions")

        for field, value in data.items():
            setattr(suggestion, field, value)
        await self.db.commit()
        await self.db.refresh(suggestion)
        return {
            "id": suggestion.id,
            "manager_id": suggestion.manager_id,
            "patient_id": suggestion.patient_id,
            "content": suggestion.content,
            "suggestion_type": suggestion.suggestion_type,
        }

    async def delete_suggestion(
        self,
        suggestion_id: int,
        user_id: int,
        tenant_id: int,
    ) -> None:
        """撤回自己的管理建议"""
        suggestion = await self.db.get(ManagementSuggestion, suggestion_id)
        if not suggestion or suggestion.tenant_id != tenant_id:
            raise NotFoundError("Suggestion", suggestion_id)
        if suggestion.manager_id != user_id:
            raise ForbiddenError("Can only delete your own suggestions")

        await self.db.delete(suggestion)
        await self.db.commit()

    async def create_manager_profile(
        self,
        *,
        user_id: int,
        tenant_id: int,
        org_id: int,
        title: str | None = None,
        bio: str | None = None,
    ) -> dict:
        """创建管理师档案"""
        user = await self.repo.find_user(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        existing = await self.repo.find_by_user_and_org(user_id, org_id)
        if existing:
            raise ConflictError("Manager profile already exists")

        profile = ManagerProfile(
            user_id=user_id,
            tenant_id=tenant_id,
            org_id=org_id,
            title=title,
            bio=bio,
        )
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        await self.db.commit()
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "org_id": profile.org_id,
            "title": profile.title,
            "bio": profile.bio,
            "is_active": profile.is_active,
        }

    async def update_manager_profile(
        self,
        profile_id: int,
        tenant_id: int,
        org_id: int | None,
        data: dict,
    ) -> dict:
        """更新管理师档案"""
        profile = await self.repo.get_by_id(profile_id)
        if not profile or profile.tenant_id != tenant_id:
            raise NotFoundError("Manager profile", profile_id)
        if org_id is not None and profile.org_id != org_id:
            raise NotFoundError("Manager profile", profile_id)

        for field, value in data.items():
            setattr(profile, field, value)
        await self.db.commit()
        await self.db.refresh(profile)
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "org_id": profile.org_id,
            "title": profile.title,
            "bio": profile.bio,
            "is_active": profile.is_active,
        }

    async def deactivate_manager_profile(
        self,
        profile_id: int,
        tenant_id: int,
        org_id: int | None,
    ) -> None:
        """停用管理师档案"""
        profile = await self.repo.get_by_id(profile_id)
        if not profile or profile.tenant_id != tenant_id:
            raise NotFoundError("Manager profile", profile_id)
        if org_id is not None and profile.org_id != org_id:
            raise NotFoundError("Manager profile", profile_id)

        profile.is_active = False
        await self.db.commit()
