"""用户管理业务服务"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func as sqlfunc

from app.base import security
from app.base.exceptions import ConflictError, NotFoundError
from app.models import OrganizationUser, OrganizationUserRole, Role, User
from app.schemas.admin import UserAdminRead


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _user_read(self, user: User) -> UserAdminRead:
        """构建用户管理视图 DTO"""
        count_stmt = select(func.count()).where(OrganizationUser.user_id == user.id)
        count = (await self.db.execute(count_stmt)).scalar() or 0
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
        stmt = select(User).where(User.email == email)
        if (await self.db.execute(stmt)).scalar_one_or_none():
            raise ConflictError("User already exists")

        user = User(
            email=email,
            password_hash=security.get_password_hash(password),
            name=name,
        )
        self.db.add(user)
        await self.db.flush()

        org_user = OrganizationUser(
            tenant_id=tenant_id, org_id=org_id, user_id=user.id, user_type="staff"
        )
        self.db.add(org_user)
        await self.db.flush()

        if role_ids:
            for rid in role_ids:
                self.db.add(
                    OrganizationUserRole(
                        tenant_id=tenant_id, org_id=org_id, user_id=user.id, role_id=rid
                    )
                )
        else:
            stmt_role = select(Role).where(
                Role.code == "staff",
                (Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)),
            )
            staff_role = (await self.db.execute(stmt_role)).scalars().first()
            if staff_role:
                self.db.add(
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
        base = (
            select(User)
            .join(OrganizationUser, OrganizationUser.user_id == User.id)
            .where(OrganizationUser.tenant_id == tenant_id)
            .distinct()
        )
        if search:
            base = base.where(
                User.email.ilike(f"%{search}%") | User.name.ilike(f"%{search}%")
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = base.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        users = result.scalars().all()

        user_reads = [await self._user_read(u) for u in users]
        return {"total": total, "items": user_reads}

    async def get_user(self, user_id: int) -> UserAdminRead:
        """获取用户详情"""
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User", user_id)
        return await self._user_read(user)

    async def update_user(self, user_id: int, data: dict) -> UserAdminRead:
        """编辑用户信息"""
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User", user_id)

        if "email" in data and data["email"] and data["email"] != user.email:
            dup = select(User).where(User.email == data["email"], User.id != user_id)
            if (await self.db.execute(dup)).scalar_one_or_none():
                raise ConflictError("Email already in use")
            user.email = data["email"]
        if "name" in data and data["name"] is not None:
            user.name = data["name"]

        await self.db.commit()
        await self.db.refresh(user)
        return await self._user_read(user)

    async def update_user_status(self, user_id: int, is_active: bool) -> None:
        """启用/禁用用户"""
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User", user_id)
        user.deleted_at = None if is_active else sqlfunc.now()
        await self.db.commit()

    async def delete_user(self, user_id: int) -> None:
        """软删除用户"""
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User", user_id)
        user.deleted_at = sqlfunc.now()
        await self.db.commit()
