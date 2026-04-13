from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import OrganizationUser, PasswordResetToken, User
from app.repositories.base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, PasswordResetToken)

    async def get_valid_token(self, email: str, code: str) -> PasswordResetToken | None:
        stmt = (
            select(self.model)
            .join(User, User.id == self.model.user_id)
            .where(
                User.email == email,
                self.model.token == code,
                self.model.used == False,
            )
            .order_by(self.model.created_at.desc())
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()


class AuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_orgs_with_tenant(self, user_id: int) -> list[OrganizationUser]:
        from app.models import Organization, Tenant
        stmt = (
            select(OrganizationUser)
            .join(Organization, Organization.id == OrganizationUser.org_id)
            .join(Tenant, Tenant.id == Organization.tenant_id)
            .options(
                selectinload(OrganizationUser.organization),
                selectinload(OrganizationUser.rbac_roles),
            )
            .where(OrganizationUser.user_id == user_id, Tenant.status == "active")
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_org_user_with_roles(self, user_id: int, org_id: int) -> OrganizationUser | None:
        stmt = (
            select(OrganizationUser)
            .where(OrganizationUser.user_id == user_id, OrganizationUser.org_id == org_id)
            .options(selectinload(OrganizationUser.rbac_roles))
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()
