"""组织管理业务服务"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models import (
    Organization,
    OrganizationInvitation,
    OrganizationUser,
    OrganizationUserRole,
    User,
)
from app.repositories.org_invitation_repo import OrganizationInvitationRepository
from app.repositories.org_repo import OrganizationRepository
from app.repositories.org_user_repo import OrganizationUserRepository, OrganizationUserRoleRepository
from app.repositories.role_repo import RoleRepository
from app.repositories.user_repo import UserRepository


class OrgService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrganizationRepository(db)
        self.org_user_repo = OrganizationUserRepository(db)
        self.org_user_role_repo = OrganizationUserRoleRepository(db)
        self.invitation_repo = OrganizationInvitationRepository(db)
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    async def get_my_organizations(self, user_id: int) -> list[Organization]:
        """获取用户所属的所有组织"""
        return await self.repo.list_user_orgs(user_id=user_id)

    async def list_organizations(
        self,
        tenant_id: int,
        *,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> dict:
        """按租户列出组织"""
        total, items = await self.repo.list_by_tenant(tenant_id, search=search, skip=skip, limit=limit)
        return {"total": total, "items": items}

    async def create_organization(
        self, *, tenant_id: int, name: str, code: str, **kwargs
    ) -> Organization:
        """创建组织"""
        if await self.repo.check_code_exists(tenant_id, code):
            raise ConflictError("Organization code already exists in this tenant")

        org = Organization(tenant_id=tenant_id, name=name, code=code, **kwargs)
        await self.repo.create(org)
        await self.db.commit()
        return org

    async def update_organization(
        self, org_id: int, data: dict
    ) -> Organization:
        """编辑组织"""
        org = await self.repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organization", org_id)

        await self.repo.update(org, data)
        await self.db.commit()
        return org

    async def delete_organization(self, org_id: int) -> None:
        """删除组织（检查成员）"""
        org = await self.repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organization", org_id)

        member_count = await self.org_user_repo.count(filters=[OrganizationUser.org_id == org_id])
        if member_count > 0:
            raise ConflictError(
                f"Organization still has {member_count} member(s). Remove them first."
            )

        await self.repo.delete(org)
        await self.db.commit()

    async def get_members(self, org_id: int) -> list[dict]:
        """获取组织成员列表 (含角色)"""
        org_users = await self.repo.get_members_with_roles(org_id)
        members = []
        for org_user in org_users:
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
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        count = await self.org_user_repo.count(filters=[
            OrganizationUser.org_id == org_id,
            OrganizationUser.user_id == user_id
        ])
        if count > 0:
            raise ConflictError("User is already a member of this organization")

        org_user = OrganizationUser(
            tenant_id=tenant_id, org_id=org_id, user_id=user_id, user_type=user_type
        )
        await self.org_user_repo.create(org_user)

        for rid in role_ids:
            await self.org_user_role_repo.create(
                OrganizationUserRole(
                    tenant_id=tenant_id, org_id=org_id, user_id=user_id, role_id=rid
                )
            )
        await self.db.commit()

    async def remove_member(self, org_id: int, user_id: int) -> None:
        """移除组织成员"""
        # Since repo delete takes an instance, we first find it.
        org_user = await self.org_user_repo.get_by_org_and_user(org_id, user_id)
        if not org_user:
            raise NotFoundError("Member")
        await self.org_user_repo.delete(org_user)
        from sqlalchemy import select
        # Also clean up roles
        roles_stmt = select(OrganizationUserRole).where(
            OrganizationUserRole.org_id == org_id, OrganizationUserRole.user_id == user_id
        )
        for r_link in (await self.db.execute(roles_stmt)).scalars().all():
            await self.org_user_role_repo.delete(r_link)
        await self.db.commit()

    async def list_invitations(self, org_id: int) -> list[OrganizationInvitation]:
        """列出待处理邀请"""
        return await self.invitation_repo.list_pending(org_id)

    async def create_invitation(
        self, *, org_id: int, tenant_id: int, inviter_id: int, email: str, role: str
    ) -> OrganizationInvitation:
        """发起组织邀请"""
        target_user = await self.user_repo.get_by_email(email)
        if target_user:
            count = await self.org_user_repo.count(filters=[
                OrganizationUser.org_id == org_id,
                OrganizationUser.user_id == cast(int, target_user.id)
            ])
            if count > 0:
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
        await self.invitation_repo.create(invitation)
        await self.db.commit()
        return invitation

    async def accept_invitation(self, token: str, user: User) -> dict:
        """接受组织邀请"""
        invitation = await self.invitation_repo.get_pending_by_token(token)
        if not invitation:
            raise NotFoundError("Invitation")

        if invitation.expires_at.tzinfo is None:
            now = datetime.utcnow()
        else:
            now = datetime.now(timezone.utc)

        if invitation.expires_at < now:
            await self.invitation_repo.update(invitation, {"status": "expired"})
            await self.db.commit()
            raise ForbiddenError("Invitation has expired")

        if user.email != invitation.email:
            raise ForbiddenError("Invitation is for another email address")

        org = await self.repo.get_by_id(invitation.org_id)
        t_id = org.tenant_id if org else None

        org_user = OrganizationUser(
            tenant_id=t_id, org_id=invitation.org_id, user_id=user.id, user_type="staff"
        )
        await self.org_user_repo.create(org_user)

        role = await self.role_repo.get_staff_role(t_id) # Using staff fallback or specific get

        if role:
            await self.org_user_role_repo.create(
                OrganizationUserRole(
                    tenant_id=t_id, org_id=invitation.org_id, user_id=user.id, role_id=role.id
                )
            )

        invitation.status = "accepted"
        await self.db.commit()
        return {"message": "You have joined the organization successfully"}
