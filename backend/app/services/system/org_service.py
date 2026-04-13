"""组织管理业务服务"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.base.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models import (
    Organization,
    OrganizationInvitation,
    OrganizationUser,
    OrganizationUserRole,
    Role,
    User,
)


class OrgService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_my_organizations(self, user_id: int) -> list[Organization]:
        """获取用户所属的所有组织"""
        stmt = (
            select(Organization)
            .join(OrganizationUser)
            .where(OrganizationUser.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_organizations(
        self,
        tenant_id: int,
        *,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> dict:
        """按租户列出组织"""
        base = select(Organization).where(Organization.tenant_id == tenant_id)
        if search:
            base = base.where(
                Organization.name.ilike(f"%{search}%")
                | Organization.code.ilike(f"%{search}%")
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            base.order_by(Organization.sort, Organization.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return {"total": total, "items": list(result.scalars().all())}

    async def create_organization(
        self, *, tenant_id: int, name: str, code: str, **kwargs
    ) -> Organization:
        """创建组织"""
        # code 唯一性检查
        stmt = select(Organization).where(
            Organization.tenant_id == tenant_id,
            Organization.code == code,
        )
        if (await self.db.execute(stmt)).scalar_one_or_none():
            raise ConflictError("Organization code already exists in this tenant")

        org = Organization(tenant_id=tenant_id, name=name, code=code, **kwargs)
        self.db.add(org)
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def update_organization(
        self, org_id: int, data: dict
    ) -> Organization:
        """编辑组织"""
        org = await self.db.get(Organization, org_id)
        if not org:
            raise NotFoundError("Organization", org_id)

        for field, value in data.items():
            setattr(org, field, value)
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def delete_organization(self, org_id: int) -> None:
        """删除组织（检查成员）"""
        org = await self.db.get(Organization, org_id)
        if not org:
            raise NotFoundError("Organization", org_id)

        member_count = (
            await self.db.execute(
                select(func.count()).where(OrganizationUser.org_id == org_id)
            )
        ).scalar() or 0
        if member_count > 0:
            raise ConflictError(
                f"Organization still has {member_count} member(s). Remove them first."
            )

        await self.db.delete(org)
        await self.db.commit()

    async def get_members(self, org_id: int) -> list[dict]:
        """获取组织成员列表 (含角色)"""
        stmt = (
            select(OrganizationUser)
            .options(
                selectinload(OrganizationUser.user),
                selectinload(OrganizationUser.rbac_roles).selectinload(Role.permissions),
            )
            .where(OrganizationUser.org_id == org_id)
        )
        result = await self.db.execute(stmt)
        members = []
        for org_user in result.scalars().all():
            members.append(
                {
                    "user_id": org_user.user.id,
                    "email": org_user.user.email,
                    "name": org_user.user.name,
                    "roles": [r.code for r in org_user.rbac_roles],
                    "user_type": org_user.user_type,
                }
            )
        return members

    async def add_member(
        self, *, org_id: int, tenant_id: int, user_id: int, role_ids: list[int], user_type: str
    ) -> None:
        """添加成员到组织"""
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User", user_id)

        stmt = select(OrganizationUser).where(
            OrganizationUser.org_id == org_id,
            OrganizationUser.user_id == user_id,
        )
        if (await self.db.execute(stmt)).scalar_one_or_none():
            raise ConflictError("User is already a member of this organization")

        org_user = OrganizationUser(
            tenant_id=tenant_id, org_id=org_id, user_id=user_id, user_type=user_type
        )
        self.db.add(org_user)
        await self.db.flush()

        for rid in role_ids:
            self.db.add(
                OrganizationUserRole(
                    tenant_id=tenant_id, org_id=org_id, user_id=user_id, role_id=rid
                )
            )
        await self.db.commit()

    async def remove_member(self, org_id: int, user_id: int) -> None:
        """移除组织成员"""
        stmt = delete(OrganizationUser).where(
            OrganizationUser.org_id == org_id, OrganizationUser.user_id == user_id
        )
        result = await self.db.execute(stmt)
        if result.rowcount == 0:
            raise NotFoundError("Member")
        await self.db.commit()

    async def list_invitations(self, org_id: int) -> list[OrganizationInvitation]:
        """列出待处理邀请"""
        stmt = select(OrganizationInvitation).where(
            OrganizationInvitation.org_id == org_id,
            OrganizationInvitation.status == "pending",
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_invitation(
        self, *, org_id: int, tenant_id: int, inviter_id: int, email: str, role: str
    ) -> OrganizationInvitation:
        """发起组织邀请"""
        # 如果用户已是成员则拒绝
        user_stmt = select(User).where(User.email == email)
        target_user = (await self.db.execute(user_stmt)).scalar_one_or_none()
        if target_user:
            member_stmt = select(OrganizationUser).where(
                OrganizationUser.org_id == org_id,
                OrganizationUser.user_id == target_user.id,
            )
            if (await self.db.execute(member_stmt)).scalar_one_or_none():
                raise ConflictError("User is already a member")

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = OrganizationInvitation(
            tenant_id=tenant_id,
            org_id=org_id,
            inviter_id=inviter_id,
            email=email,
            role=role,
            token=token,
            status="pending",
            expires_at=expires_at,
        )
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def accept_invitation(self, token: str, user: User) -> dict:
        """接受组织邀请"""
        stmt = select(OrganizationInvitation).where(
            OrganizationInvitation.token == token,
            OrganizationInvitation.status == "pending",
        )
        invitation = (await self.db.execute(stmt)).scalar_one_or_none()
        if not invitation:
            raise NotFoundError("Invitation")

        # 时区兼容处理
        if invitation.expires_at.tzinfo is None:
            now = datetime.utcnow()
        else:
            now = datetime.now(timezone.utc)

        if invitation.expires_at < now:
            invitation.status = "expired"
            await self.db.commit()
            raise ForbiddenError("Invitation has expired")

        if user.email != invitation.email:
            raise ForbiddenError("Invitation is for another email address")

        org = await self.db.get(Organization, invitation.org_id)
        t_id = org.tenant_id if org else None

        org_user = OrganizationUser(
            tenant_id=t_id, org_id=invitation.org_id, user_id=user.id, user_type="staff"
        )
        self.db.add(org_user)

        # 查找角色
        role_stmt = select(Role).where(Role.code == invitation.role, Role.tenant_id == t_id)
        role = (await self.db.execute(role_stmt)).scalar_one_or_none()
        if not role:
            sys_role_stmt = select(Role).where(
                Role.code == invitation.role, Role.tenant_id.is_(None)
            )
            role = (await self.db.execute(sys_role_stmt)).scalar_one_or_none()

        if role:
            self.db.add(
                OrganizationUserRole(
                    tenant_id=t_id, org_id=invitation.org_id, user_id=user.id, role_id=role.id
                )
            )

        invitation.status = "accepted"
        await self.db.commit()
        return {"message": "You have joined the organization successfully"}
