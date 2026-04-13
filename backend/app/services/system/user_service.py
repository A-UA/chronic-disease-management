"""用户管理业务服务"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func as sqlfunc

from app.base import security
from app.base.exceptions import ConflictError, NotFoundError
from app.models import OrganizationUser, OrganizationUserRole, User
from app.repositories.org_user_repo import (
    OrganizationUserRepository,
    OrganizationUserRoleRepository,
)
from app.repositories.role_repo import RoleRepository
from app.repositories.user_repo import UserRepository
from app.schemas.admin import UserAdminRead


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)
        self.org_user_repo = OrganizationUserRepository(db)
        self.org_user_role_repo = OrganizationUserRoleRepository(db)
        self.role_repo = RoleRepository(db)

    async def _user_read(self, user: User) -> UserAdminRead:
        """构建用户管理视图 DTO"""
        count = await self.org_user_repo.count(filters=[OrganizationUser.user_id == user.id])
        return UserAdminRead(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
            org_count=count,
        )

    async def create_user(
        self,
        *,
        email: str,
        password: str,
        name: str | None,
        tenant_id: int,
        org_id: int,
        role_ids: list[int] | None = None,
    ) -> UserAdminRead:
        """创建用户并绑定组织+角色"""
        if await self.repo.get_by_email(email):
            raise ConflictError("User already exists")

        user = User(
            email=email,
            password_hash=security.get_password_hash(password),
            name=name,
        )
        await self.repo.create(user)

        org_user = OrganizationUser(
            tenant_id=tenant_id, org_id=org_id, user_id=user.id, user_type="staff"
        )
        await self.org_user_repo.create(org_user)

        if role_ids:
            for rid in role_ids:
                await self.org_user_role_repo.create(
                    OrganizationUserRole(
                        tenant_id=tenant_id, org_id=org_id, user_id=user.id, role_id=rid
                    )
                )
        else:
            staff_role = await self.role_repo.get_staff_role(tenant_id=tenant_id)
            if staff_role:
                await self.org_user_role_repo.create(
                    OrganizationUserRole(
                        tenant_id=tenant_id, org_id=org_id, user_id=user.id, role_id=staff_role.id
                    )
                )

        await self.db.commit()
        await self.db.refresh(user)
        return UserAdminRead(
            id=user.id, email=user.email, name=user.name, created_at=user.created_at, org_count=1
        )

    async def list_users(
        self,
        tenant_id: int,
        *,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict:
        """列出租户下用户"""
        total, users = await self.repo.list_by_tenant(
            tenant_id=tenant_id, search=search, skip=skip, limit=limit
        )

        user_reads = [await self._user_read(u) for u in users]
        return {"total": total, "items": user_reads}

    async def get_user(self, user_id: int) -> UserAdminRead:
        """获取用户详情"""
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        return await self._user_read(user)

    async def update_user(self, user_id: int, data: dict) -> UserAdminRead:
        """编辑用户信息"""
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        if "email" in data and data["email"] and data["email"] != user.email:
            if await self.repo.get_by_email(data["email"], exclude_id=user_id):
                raise ConflictError("Email already in use")

        await self.repo.update(user, data)
        await self.db.commit()

        return await self._user_read(user)

    async def update_user_status(self, user_id: int, is_active: bool) -> None:
        """启用/禁用用户"""
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        await self.repo.update(user, {"deleted_at": None if is_active else sqlfunc.now()})
        await self.db.commit()

    async def delete_user(self, user_id: int) -> None:
        """软删除用户"""
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        await self.repo.update(user, {"deleted_at": sqlfunc.now()})
        await self.db.commit()
