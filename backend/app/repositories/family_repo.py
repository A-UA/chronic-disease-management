from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PatientFamilyLink
from app.repositories.base import BaseRepository


class FamilyRepository(BaseRepository[PatientFamilyLink]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, PatientFamilyLink)

    async def get_active_link(self, patient_id: int, user_id: int) -> PatientFamilyLink | None:
        stmt = select(self.model).where(
            self.model.patient_id == patient_id,
            self.model.family_user_id == user_id,
            self.model.status == "active",
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_link(self, patient_id: int, user_id: int) -> PatientFamilyLink | None:
        stmt = select(self.model).where(
            self.model.patient_id == patient_id,
            self.model.family_user_id == user_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_by_family_user(self, user_id: int) -> list[PatientFamilyLink]:
        stmt = select(self.model).where(
            self.model.family_user_id == user_id,
            self.model.status == "active",
        )
        return list((await self.db.execute(stmt)).scalars().all())
